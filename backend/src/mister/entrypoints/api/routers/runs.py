import re
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import ValidationError

from mister.entrypoints.api.errors import domain_error_handler, problem
from mister.entrypoints.api.schemas import (
    AdvanceBody,
    Problem,
    RunView,
    StartRunBody,
    StartRunResponse,
    TakeDecisionBody,
)
from mister.shared_kernel.ids import DilemmaId, OptionId, PlayableSeasonId, RunId

router = APIRouter(prefix="/api/runs", tags=["Runs"])
_UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
_MIN_KEY_LENGTH = 8
_MAX_KEY_LENGTH = 128
_BearerAuth = Annotated[
    HTTPAuthorizationCredentials | None,
    Depends(HTTPBearer(scheme_name="runToken", auto_error=False)),
]
_SLUG_SCHEMA = {
    "type": "string",
    "pattern": r"^[a-z0-9]+(-[a-z0-9]+)*$",
    "minLength": 1,
    "maxLength": 64,
}
_START_BODY_SCHEMA = {
    "type": "object",
    "required": ["seasonId"],
    "additionalProperties": False,
    "properties": {"seasonId": _SLUG_SCHEMA},
}
_DECISION_BODY_SCHEMA = {
    "type": "object",
    "required": ["expectedVersion", "dilemmaId", "optionId"],
    "additionalProperties": False,
    "properties": {
        "expectedVersion": {"type": "integer", "minimum": 0},
        "dilemmaId": _SLUG_SCHEMA,
        "optionId": _SLUG_SCHEMA,
    },
}
_ADVANCE_BODY_SCHEMA = {
    "type": "object",
    "required": ["expectedVersion"],
    "additionalProperties": False,
    "properties": {"expectedVersion": {"type": "integer", "minimum": 0}},
}


def _problem_responses(*statuses: int) -> dict[int | str, dict[str, Any]]:
    return {
        status: {
            "description": "Problem details.",
            "model": Problem,
        }
        for status in statuses
    }


def _run_id(value: str) -> RunId:
    if not _UUID.fullmatch(value):
        raise ValueError("invalid run id")
    return RunId(UUID(value))


def _token(request: Request) -> str | None:
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer ") or not header[7:].strip():
        return None
    return header[7:].strip()


async def _json_model(request: Request, model: Any) -> Any:
    if (
        request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        != "application/json"
    ):
        raise ValueError("content type")
    data = await request.json()
    return model.model_validate(data)


def _invalid(error: Exception) -> JSONResponse:
    errors = None
    if isinstance(error, ValidationError):
        aliases = {
            "season_id": "seasonId",
            "expected_version": "expectedVersion",
            "dilemma_id": "dilemmaId",
            "option_id": "optionId",
        }
        errors = [
            {
                "field": aliases.get(
                    str(item["loc"][-1]) if item["loc"] else "body",
                    str(item["loc"][-1]) if item["loc"] else "body",
                ),
                "message": item["msg"],
            }
            for item in error.errors()
        ]
    return problem(400, "validation_error", "The request body is not valid.", errors)


async def _authenticate(
    api: Any, run_id: RunId, request: Request
) -> tuple[str | None, JSONResponse | None]:
    token = _token(request)
    if token is None:
        return None, problem(401, "run_token_required", "Send the run token as a Bearer token.")
    try:
        await run_in_threadpool(api.authenticate, run_id, token)
    except Exception as error:
        code = getattr(error, "code", "")
        if code == "run_not_found":
            return None, problem(404, code, "There is no run with that id.")
        if code in {"run_access_denied", "run_token_invalid"}:
            return None, problem(
                403, "run_token_invalid", "The run token is not valid for this run."
            )
        return None, problem(500, "internal_error", "An internal error occurred.")
    return token, None


@router.post(
    "",
    status_code=201,
    operation_id="startRun",
    response_model=StartRunResponse,
    response_model_exclude_unset=True,
    responses={
        **_problem_responses(400, 404, 429),
        201: {
            "description": "The run was created.",
            "headers": {
                "Location": {
                    "description": "Relative URL of the new run.",
                    "schema": {"type": "string"},
                }
            },
            "content": {
                "application/json": {"schema": {"$ref": "#/components/schemas/StartRunResponse"}}
            },
        },
    },
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {"application/json": {"schema": _START_BODY_SCHEMA}},
        }
    },
)
async def start_run(request: Request, response: Response) -> Any:
    try:
        body = await _json_model(request, StartRunBody)
    except Exception as error:
        return _invalid(error)
    api = request.app.state.runtime.api()
    try:
        started = await run_in_threadpool(api.start_run, PlayableSeasonId(body.season_id))
    except Exception as error:
        code = getattr(error, "code", "")
        if code == "season_not_found":
            return problem(404, code, "There is no playable season with that id.")
        return problem(500, "internal_error", "An internal error occurred.")
    payload = started.to_json()
    run_id = payload["run"]["runId"]
    response.headers["Location"] = f"/api/runs/{run_id}"
    return payload


@router.get(
    "/{runId}",
    operation_id="getRun",
    response_model=RunView,
    response_model_exclude_unset=True,
    responses=_problem_responses(400, 401, 403, 404, 429),
)
async def get_run(
    request: Request,
    _bearer: _BearerAuth,
    run_id_value: str = Path(alias="runId", json_schema_extra={"format": "uuid"}),
) -> Any:
    try:
        run_id = _run_id(run_id_value)
    except ValueError:
        return problem(400, "validation_error", "The runId is malformed.")
    api = request.app.state.runtime.api()
    token, failure = await _authenticate(api, run_id, request)
    if failure:
        return failure
    try:
        value = await run_in_threadpool(api.get_run, run_id, token)
        return value.to_json()
    except Exception as error:
        return await domain_error_handler(request, error)


async def _command(run_id_value: str, request: Request, *, decision: bool) -> Any:  # noqa: PLR0911
    try:
        run_id = _run_id(run_id_value)
    except ValueError:
        return problem(400, "validation_error", "The runId is malformed.")
    api = request.app.state.runtime.api()
    token, failure = await _authenticate(api, run_id, request)
    if failure:
        return failure
    key = request.headers.get("idempotency-key")
    if key is None:
        return problem(400, "idempotency_key_required", "Send an Idempotency-Key header.")
    if not _MIN_KEY_LENGTH <= len(key) <= _MAX_KEY_LENGTH:
        return problem(400, "validation_error", "The Idempotency-Key length is invalid.")
    try:
        body = await _json_model(request, TakeDecisionBody if decision else AdvanceBody)
    except Exception as error:
        return _invalid(error)
    try:
        if decision:
            value = await run_in_threadpool(
                api.take_decision,
                run_id,
                token,
                key,
                body.expected_version,
                DilemmaId(body.dilemma_id),
                OptionId(body.option_id),
            )
        else:
            value = await run_in_threadpool(
                api.advance_block, run_id, token, key, body.expected_version
            )
        return value.to_json()
    except Exception as error:
        return await domain_error_handler(request, error)


@router.post(
    "/{runId}/decisions",
    operation_id="takeDecision",
    response_model=RunView,
    response_model_exclude_unset=True,
    responses=_problem_responses(400, 401, 403, 404, 409, 422, 429),
    openapi_extra={
        "parameters": [
            {
                "name": "Idempotency-Key",
                "in": "header",
                "required": True,
                "schema": {"type": "string", "minLength": 8, "maxLength": 128},
            }
        ],
        "requestBody": {
            "required": True,
            "content": {"application/json": {"schema": _DECISION_BODY_SCHEMA}},
        },
    },
)
async def take_decision(
    request: Request,
    _bearer: _BearerAuth,
    run_id: str = Path(alias="runId", json_schema_extra={"format": "uuid"}),
) -> Any:
    return await _command(run_id, request, decision=True)


@router.post(
    "/{runId}/advance",
    operation_id="advanceBlock",
    response_model=RunView,
    response_model_exclude_unset=True,
    responses=_problem_responses(400, 401, 403, 404, 409, 422, 429),
    openapi_extra={
        "parameters": [
            {
                "name": "Idempotency-Key",
                "in": "header",
                "required": True,
                "schema": {"type": "string", "minLength": 8, "maxLength": 128},
            }
        ],
        "requestBody": {
            "required": True,
            "content": {"application/json": {"schema": _ADVANCE_BODY_SCHEMA}},
        },
    },
)
async def advance_block(
    request: Request,
    _bearer: _BearerAuth,
    run_id: str = Path(alias="runId", json_schema_extra={"format": "uuid"}),
) -> Any:
    return await _command(run_id, request, decision=False)
