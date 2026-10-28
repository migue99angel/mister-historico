import re
from collections.abc import AsyncIterator
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

import pytest
import yaml
from httpx import ASGITransport, AsyncClient, Response

from mister.entrypoints.api.app import create_app
from mister.shared_kernel.ids import PlayableSeasonId, RunId

if TYPE_CHECKING:
    from mister.bootstrap import Container

_CONTRACT_PATH = Path(__file__).parents[5] / "contracts" / "openapi.yaml"
JsonObject = dict[str, Any]
_CONTRACT: JsonObject = yaml.safe_load(_CONTRACT_PATH.read_text())


def _matches_schema(  # noqa: PLR0911, PLR0912
    schema: JsonObject, value: Any, schemas: JsonObject
) -> bool:
    if "$ref" in schema:
        return _matches_schema(schemas[schema["$ref"].rsplit("/", 1)[-1]], value, schemas)
    if "allOf" in schema:
        return all(_matches_schema(part, value, schemas) for part in schema["allOf"])
    if "oneOf" in schema:
        return sum(_matches_schema(part, value, schemas) for part in schema["oneOf"]) == 1
    if "anyOf" in schema:
        return any(_matches_schema(part, value, schemas) for part in schema["anyOf"])
    if "enum" in schema and value not in schema["enum"]:
        return False
    expected_type = schema.get("type")
    if isinstance(expected_type, list):
        if value is None:
            return "null" in expected_type
        expected_type = next((kind for kind in expected_type if kind != "null"), None)
    if expected_type == "object":
        if not isinstance(value, dict) or not set(schema.get("required", [])) <= value.keys():
            return False
        if (
            schema.get("additionalProperties") is False
            and value.keys() - schema.get("properties", {}).keys()
        ):
            return False
        return all(
            key not in schema.get("properties", {})
            or _matches_schema(schema["properties"][key], item, schemas)
            for key, item in value.items()
        )
    if expected_type == "array":
        return (
            isinstance(value, list)
            and len(value) >= schema.get("minItems", 0)
            and all(_matches_schema(schema["items"], item, schemas) for item in value)
        )
    if expected_type == "string":
        if not isinstance(value, str):
            return False
        if "pattern" in schema and re.fullmatch(schema["pattern"], value) is None:
            return False
        if schema.get("format") == "uuid":
            try:
                UUID(value)
            except ValueError:
                return False
        if schema.get("format") == "date":
            try:
                date.fromisoformat(value)
            except ValueError:
                return False
        minimum = int(schema.get("minLength", 0))
        maximum = int(schema.get("maxLength", 10**9))
        return len(value) >= minimum and len(value) <= maximum
    if expected_type == "integer":
        return (
            type(value) is int
            and value >= schema.get("minimum", value)
            and value <= schema.get("maximum", value)
        )
    if expected_type == "number":
        return (
            type(value) in (int, float)
            and value >= schema.get("minimum", value)
            and value <= schema.get("maximum", value)
        )
    if expected_type == "boolean":
        return type(value) is bool
    if expected_type == "null":
        return value is None
    return True


def _assert_contract_response(response: Response, path: str, method: str, status: int) -> None:
    operation = _CONTRACT["paths"][path][method]
    response_schema = _resolve_schema(operation["responses"][str(status)], _CONTRACT)
    media_type = "application/json" if status < 400 else "application/problem+json"
    schema_ref = response_schema["content"][media_type]["schema"]
    assert _matches_schema(schema_ref, response.json(), _CONTRACT["components"]["schemas"])


def _resolve_schema(schema: JsonObject, document: JsonObject) -> JsonObject:
    if "$ref" not in schema:
        return schema
    current = document
    for part in schema["$ref"].removeprefix("#/").split("/"):
        current = current[part]
    return current


def _schema_types(schema: JsonObject, document: JsonObject) -> set[str]:
    schema = _resolve_schema(schema, document)
    if "type" in schema:
        value = schema["type"]
        return {str(item) for item in (value if isinstance(value, list) else [value])}
    alternatives = schema.get("oneOf", schema.get("anyOf", schema.get("allOf", []))) or []
    return set().union(*(_schema_types(item, document) for item in alternatives))


def _schema_enum(schema: JsonObject, document: JsonObject) -> set[Any]:
    schema = _resolve_schema(schema, document)
    if "enum" in schema:
        return set(schema["enum"])
    alternatives = schema.get("allOf", schema.get("oneOf", schema.get("anyOf", []))) or []
    for alternative in alternatives:
        values = _schema_enum(alternative, document)
        if values:
            return values
    return set()


def _assert_schema_conforms(
    actual: JsonObject,
    authored: JsonObject,
    actual_doc: JsonObject,
    authored_doc: JsonObject,
) -> None:
    actual = _resolve_schema(actual, actual_doc)
    authored = _resolve_schema(authored, authored_doc)
    assert _schema_types(actual, actual_doc) == _schema_types(authored, authored_doc)
    authored_enum = _schema_enum(authored, authored_doc)
    if authored_enum:
        assert _schema_enum(actual, actual_doc) == authored_enum
    authored_alternatives = authored.get("oneOf", authored.get("anyOf"))
    actual_alternatives = actual.get("oneOf", actual.get("anyOf"))
    if authored_alternatives and actual_alternatives:
        for expected in authored_alternatives:
            expected_types = _schema_types(expected, authored_doc)
            matching = [
                item
                for item in actual_alternatives
                if _schema_types(item, actual_doc) == expected_types
            ]
            assert len(matching) == 1
            _assert_schema_conforms(matching[0], expected, actual_doc, authored_doc)
        return
    for constraint in (
        "format",
        "pattern",
        "minLength",
        "maxLength",
        "minimum",
        "maximum",
        "minItems",
        "maxItems",
    ):
        if constraint in authored:
            actual_value = actual.get(constraint)
            if actual_value is None:
                alternatives = actual.get("oneOf", actual.get("anyOf", [])) or []
                actual_value = next(
                    (item[constraint] for item in alternatives if constraint in item), None
                )
            assert actual_value == authored[constraint]
    if authored.get("type") == "object":
        assert set(actual.get("required", [])) == set(authored.get("required", []))
        assert set(actual.get("properties", {})) == set(authored.get("properties", {}))
        if authored.get("additionalProperties") is False:
            assert actual.get("additionalProperties") is False
        for name, expected in authored.get("properties", {}).items():
            _assert_schema_conforms(actual["properties"][name], expected, actual_doc, authored_doc)
    if authored.get("type") == "array":
        _assert_schema_conforms(actual["items"], authored["items"], actual_doc, authored_doc)


class _Presented:
    def __init__(self, value: JsonObject) -> None:
        self.value = value

    def to_json(self) -> JsonObject:
        return self.value


class _Started:
    run_token = "A" * 43

    def __init__(self) -> None:
        self.view = _Presented(_run_json())

    def to_json(self) -> JsonObject:
        return {"runToken": self.run_token, "run": self.view.to_json()}


class _PublicError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class _GameApi:
    def list_seasons(self) -> tuple[_Presented, ...]:
        return (_Presented(_season_summary()),)

    def get_season(self, season_id: PlayableSeasonId) -> _Presented:
        if season_id.value == "missing-season":
            raise _PublicError("season_not_found")
        return _Presented(
            {
                **_season_summary(),
                "presentation": "A test season.",
                "boardObjectives": [],
                "squad": {"size": 0, "averageRating": 1, "keyPlayers": []},
                "competitions": [],
                "blockCount": 5,
            }
        )

    def start_run(self, season_id: PlayableSeasonId) -> _Started:
        if season_id.value == "missing-season":
            raise _PublicError("season_not_found")
        return _Started()

    def authenticate(self, run_id: RunId, token: str) -> None:
        return None

    def get_run(self, run_id: RunId, token: str) -> _Presented:
        return _Presented(_run_json())

    def take_decision(self, *args: Any) -> _Presented:
        if args[-1].value == "nope":
            raise _PublicError("invalid_option")
        if args[-1].value == "already":
            raise _PublicError("dilemma_already_decided")
        value = _run_json()
        value["version"] = 1
        return _Presented(value)

    def advance_block(self, *args: Any) -> _Presented:
        if args[-1] == 77:
            raise _PublicError("pending_dilemmas")
        if args[-1] == 88:
            raise _PublicError("run_already_finished")
        value = _run_json()
        value["version"] = 1
        return _Presented(value)


def _season_summary() -> JsonObject:
    return {
        "id": "test-fc-2000-01",
        "clubName": "Test FC",
        "shortName": "TFC",
        "seasonLabel": "2000-01",
        "historicalManager": "Manager Test",
        "colors": {"primary": "#1d4ed8", "secondary": "#f8fafc"},
    }


def _run_json() -> JsonObject:
    return {
        "runId": "0b6f3a52-6c0e-4d3e-8d0a-3f1f6e2b9c11",
        "seasonId": "test-fc-2000-01",
        "status": "in_progress",
        "version": 0,
        "block": {"number": 1, "total": 5, "label": "August"},
        "pendingDilemmas": [],
        "decisions": [],
        "state": {"morale": 50, "boardConfidence": 50, "fitness": 50},
        "squad": {"size": 0, "averageRating": 1, "players": []},
        "tactic": {"style": "balanced", "system": "4-4-2"},
        "competitionPriorities": [],
        "lastBlockSummary": None,
        "sackedMonth": None,
    }


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    runtime = SimpleNamespace(api=_GameApi)
    container = cast("Container", SimpleNamespace(settings=None, engine=None))
    app = create_app(container)
    app.state.runtime = runtime
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as value:
        yield value


@pytest.mark.anyio
async def test_seasons_http_routes_return_presentation(client: AsyncClient) -> None:
    listed = await client.get("/api/seasons")
    assert listed.json() == {"items": [_season_summary()]}
    _assert_contract_response(listed, "/seasons", "get", 200)
    detail = await client.get("/api/seasons/test-fc-2000-01")
    assert detail.status_code == 200
    assert detail.json()["blockCount"] == 5
    _assert_contract_response(detail, "/seasons/{seasonId}", "get", 200)


@pytest.mark.anyio
async def test_start_run_returns_token_and_location(client: AsyncClient) -> None:
    response = await client.post("/api/runs", json={"seasonId": "test-fc-2000-01"})
    assert response.status_code == 201
    assert response.headers["location"] == "/api/runs/0b6f3a52-6c0e-4d3e-8d0a-3f1f6e2b9c11"
    assert response.json()["runToken"] == "A" * 43
    _assert_contract_response(response, "/runs", "post", 201)


@pytest.mark.anyio
async def test_run_read_and_both_commands_are_http_routes(client: AsyncClient) -> None:
    run = "0b6f3a52-6c0e-4d3e-8d0a-3f1f6e2b9c11"
    auth = {"Authorization": "Bearer fixture"}
    read = await client.get(f"/api/runs/{run}", headers=auth)
    assert read.status_code == 200
    _assert_contract_response(read, "/runs/{runId}", "get", 200)
    decision = await client.post(
        f"/api/runs/{run}/decisions",
        json={"expectedVersion": 0, "dilemmaId": "summer-striker", "optionId": "sign"},
        headers={**auth, "Idempotency-Key": "decision-123"},
    )
    advance = await client.post(
        f"/api/runs/{run}/advance",
        json={"expectedVersion": 0},
        headers={**auth, "Idempotency-Key": "advance-123"},
    )
    assert decision.status_code == advance.status_code == 200
    _assert_contract_response(decision, "/runs/{runId}/decisions", "post", 200)
    _assert_contract_response(advance, "/runs/{runId}/advance", "post", 200)


@pytest.mark.anyio
async def test_non_object_body_is_validation_error_after_authentication(
    client: AsyncClient,
) -> None:
    run = "0b6f3a52-6c0e-4d3e-8d0a-3f1f6e2b9c11"
    response = await client.post(
        f"/api/runs/{run}/advance",
        json=[],
        headers={"Authorization": "Bearer fixture", "Idempotency-Key": "advance-123"},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"
    _assert_contract_response(response, "/runs/{runId}/advance", "post", 400)


@pytest.mark.anyio
async def test_invalid_and_unknown_season_ids_are_mapped(client: AsyncClient) -> None:
    malformed = await client.get("/api/seasons/INVALID")
    assert malformed.status_code == 400
    assert malformed.json()["code"] == "validation_error"
    missing = await client.get("/api/seasons/missing-season")
    assert missing.status_code == 404
    assert missing.json()["code"] == "season_not_found"


@pytest.mark.anyio
async def test_start_body_errors_and_unknown_season_are_mapped(client: AsyncClient) -> None:
    for content, headers, expected_code in (
        ("not-json", {"Content-Type": "application/json"}, "validation_error"),
        ('{"seasonId":"test-fc-2000-01","seed":1}', {}, "validation_error"),
    ):
        response = await client.post("/api/runs", content=content, headers=headers)
        assert response.status_code == 400
        assert response.json()["code"] == expected_code
    missing = await client.post("/api/runs", json={"seasonId": "missing-season"})
    assert missing.status_code == 404
    assert missing.json()["code"] == "season_not_found"


@pytest.mark.anyio
@pytest.mark.parametrize(
    "body",
    [
        {},
        {"expectedVersion": -1},
        {"expectedVersion": "1"},
        {"expectedVersion": 1.0},
        {"expectedVersion": True},
        {"expectedVersion": None},
        {"expectedVersion": 0, "seed": 3},
    ],
)
async def test_advance_request_rejects_invalid_version_shapes(
    client: AsyncClient, body: Any
) -> None:
    run = "0b6f3a52-6c0e-4d3e-8d0a-3f1f6e2b9c11"
    response = await client.post(
        f"/api/runs/{run}/advance",
        json=body,
        headers={"Authorization": "Bearer fixture", "Idempotency-Key": "advance-123"},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"


@pytest.mark.anyio
@pytest.mark.parametrize("key", ["short", "k" * 129])
async def test_idempotency_key_length_errors_are_validation_errors(
    client: AsyncClient, key: str
) -> None:
    run = "0b6f3a52-6c0e-4d3e-8d0a-3f1f6e2b9c11"
    response = await client.post(
        f"/api/runs/{run}/advance",
        json={"expectedVersion": 0},
        headers={"Authorization": "Bearer fixture", "Idempotency-Key": key},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"


@pytest.mark.anyio
async def test_missing_idempotency_key_is_a_distinct_bad_request(client: AsyncClient) -> None:
    run = "0b6f3a52-6c0e-4d3e-8d0a-3f1f6e2b9c11"
    response = await client.post(
        f"/api/runs/{run}/advance",
        json={"expectedVersion": 0},
        headers={"Authorization": "Bearer fixture"},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "idempotency_key_required"


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("option_id", "status", "code"),
    [("nope", 422, "invalid_option"), ("already", 409, "dilemma_already_decided")],
)
async def test_decision_domain_errors_keep_their_public_codes(
    client: AsyncClient, option_id: str, status: int, code: str
) -> None:
    run = "0b6f3a52-6c0e-4d3e-8d0a-3f1f6e2b9c11"
    response = await client.post(
        f"/api/runs/{run}/decisions",
        json={"expectedVersion": 0, "dilemmaId": "summer-striker", "optionId": option_id},
        headers={"Authorization": "Bearer fixture", "Idempotency-Key": "decision-123"},
    )
    assert response.status_code == status
    assert response.json()["code"] == code


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("version", "code"), [(77, "pending_dilemmas"), (88, "run_already_finished")]
)
async def test_advance_business_errors_keep_conflict_status(
    client: AsyncClient, version: int, code: str
) -> None:
    run = "0b6f3a52-6c0e-4d3e-8d0a-3f1f6e2b9c11"
    response = await client.post(
        f"/api/runs/{run}/advance",
        json={"expectedVersion": version},
        headers={"Authorization": "Bearer fixture", "Idempotency-Key": "advance-123"},
    )
    assert response.status_code == 409
    assert response.json()["code"] == code


@pytest.mark.anyio
async def test_malformed_run_id_precedes_missing_bearer_token(client: AsyncClient) -> None:
    response = await client.post("/api/runs/not-a-uuid/advance", content="not-json")
    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"
    _assert_contract_response(response, "/runs/{runId}/advance", "post", 400)


@pytest.mark.anyio
async def test_boolean_expected_version_is_rejected_as_bad_request(
    client: AsyncClient,
) -> None:
    run = "0b6f3a52-6c0e-4d3e-8d0a-3f1f6e2b9c11"
    response = await client.post(
        f"/api/runs/{run}/advance",
        json={"expectedVersion": True},
        headers={"Authorization": "Bearer fixture", "Idempotency-Key": "advance-123"},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"
    _assert_contract_response(response, "/runs/{runId}/advance", "post", 400)


@pytest.mark.anyio
async def test_run_commands_authenticate_before_parsing_request_body(client: AsyncClient) -> None:
    run = "0b6f3a52-6c0e-4d3e-8d0a-3f1f6e2b9c11"
    response = await client.post(f"/api/runs/{run}/advance", content="not-json")
    assert response.status_code == 401
    assert response.json()["code"] == "run_token_required"
    _assert_contract_response(response, "/runs/{runId}/advance", "post", 401)


@pytest.mark.anyio
async def test_invalid_json_after_authentication_is_a_bad_request(client: AsyncClient) -> None:
    run = "0b6f3a52-6c0e-4d3e-8d0a-3f1f6e2b9c11"
    response = await client.post(
        f"/api/runs/{run}/advance",
        content="not-json",
        headers={"Authorization": "Bearer token", "Idempotency-Key": "12345678"},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"
    _assert_contract_response(response, "/runs/{runId}/advance", "post", 400)


def test_openapi_exposes_only_the_six_f3_operations() -> None:
    container = cast("Container", SimpleNamespace(settings=None, engine=None))
    app = create_app(container)
    schema = app.openapi()
    operations = {
        operation["operationId"]
        for path, methods in schema["paths"].items()
        for operation in methods.values()
        if isinstance(operation, dict) and "operationId" in operation and path.startswith("/api/")
    }
    assert operations == {
        "listSeasons",
        "getSeason",
        "startRun",
        "getRun",
        "takeDecision",
        "advanceBlock",
    }


def test_openapi_f3_shape_matches_authored_operation_contract() -> None:
    contract = _CONTRACT
    container = cast("Container", SimpleNamespace(settings=None, engine=None))
    app = create_app(container)
    document = app.openapi()
    expected_paths = {
        path: contract["paths"][path]
        for path in (
            "/seasons",
            "/seasons/{seasonId}",
            "/runs",
            "/runs/{runId}",
            "/runs/{runId}/decisions",
            "/runs/{runId}/advance",
        )
    }
    implemented = {
        path.removeprefix("/api"): item
        for path, item in document["paths"].items()
        if path.startswith(("/api/seasons", "/api/runs"))
    }
    assert set(implemented) == set(expected_paths)
    for path, operations in expected_paths.items():
        for method, authored in operations.items():
            operation = implemented[path][method]
            assert operation["operationId"] == authored["operationId"]
            assert set(operation["responses"]) >= set(authored["responses"])
            success = "201" if authored["operationId"] == "startRun" else "200"
            actual_response_schema = operation["responses"][success]["content"]["application/json"][
                "schema"
            ]
            authored_response_schema = authored["responses"][success]["content"][
                "application/json"
            ]["schema"]
            _assert_schema_conforms(
                actual_response_schema,
                authored_response_schema,
                document,
                contract,
            )
            for status, expected_response in authored["responses"].items():
                if int(status) < 400:
                    continue
                resolved_response = _resolve_schema(expected_response, contract)
                actual_content = operation["responses"][status]["content"]
                assert set(actual_content) == {"application/problem+json"}
                expected_schema = resolved_response["content"]["application/problem+json"]["schema"]
                _assert_schema_conforms(
                    actual_content["application/problem+json"]["schema"],
                    expected_schema,
                    document,
                    contract,
                )
            if "requestBody" in authored:
                body = operation["requestBody"]
                schema = body["content"]["application/json"]["schema"]
                assert body["required"] is True
                assert schema["additionalProperties"] is False
                authored_schema = authored["requestBody"]["content"]["application/json"]["schema"]
                if "$ref" in authored_schema:
                    name = authored_schema["$ref"].rsplit("/", 1)[-1]
                    authored_schema = contract["components"]["schemas"][name]
                assert set(schema["required"]) == set(authored_schema["required"])
                _assert_schema_conforms(schema, authored_schema, document, contract)
            authored_params = authored.get("parameters", [])
            expected_params = []
            for param in authored_params:
                expected_params.append(_resolve_schema(param, contract))
            actual_params = operation.get("parameters", [])
            assert {(item["in"], item["name"]) for item in actual_params} == {
                (item["in"], item["name"]) for item in expected_params
            }
            for actual_param in actual_params:
                expected_param = next(
                    item
                    for item in expected_params
                    if (item["in"], item["name"]) == (actual_param["in"], actual_param["name"])
                )
                _assert_schema_conforms(
                    actual_param["schema"], expected_param["schema"], document, contract
                )
            if authored.get("security"):
                assert operation["security"] == [{"runToken": []}]
    assert document["components"]["securitySchemes"]["runToken"]["scheme"] == "bearer"


@pytest.mark.anyio
async def test_lifespan_disposes_engine_after_exception() -> None:
    class _Engine:
        disposed = False

        def dispose(self) -> None:
            self.disposed = True

    engine = _Engine()
    container = cast("Container", SimpleNamespace(settings=None, engine=engine))
    app = create_app(container)
    with pytest.raises(RuntimeError):
        async with app.router.lifespan_context(app):
            raise RuntimeError("shutdown path")
    assert engine.disposed
