"""The exported JSON Schema (for editors) must match the Pydantic models."""

import json
from pathlib import Path

from mister.catalog.infrastructure.content_schema.export import (
    main,
    render_json_schemas,
    write_json_schemas,
)

REPO_SCHEMA_DIR = Path(__file__).parents[3] / "content" / "schema"


def test_exported_json_schema_matches_the_versioned_one() -> None:
    """Drift test. If it fails, regenerate with:
    `cd backend && uv run python -m mister.catalog.infrastructure.content_schema.export`."""
    expected = render_json_schemas()

    versioned = {p.name: p.read_text(encoding="utf-8") for p in REPO_SCHEMA_DIR.glob("*.json")}

    assert versioned == expected


def test_one_schema_is_exported_for_every_content_file_type() -> None:
    assert set(render_json_schemas()) == {
        "club.schema.json",
        "squad.schema.json",
        "aggregate.schema.json",
        "season.schema.json",
        "fixtures.schema.json",
        "standings.schema.json",
        "dilemmas.schema.json",
        "texts.schema.json",
    }


def test_the_effect_dsl_is_a_discriminated_union_in_the_dilemmas_schema() -> None:
    schema = json.loads(render_json_schemas()["dilemmas.schema.json"])

    option = schema["$defs"]["Option"]["properties"]["effects"]["items"]

    assert option["discriminator"]["propertyName"] == "type"
    assert len(option["oneOf"]) == 10


def test_rendering_is_deterministic() -> None:
    assert render_json_schemas() == render_json_schemas()


def test_write_json_schemas_creates_the_files_and_removes_stale_ones(tmp_path: Path) -> None:
    (tmp_path / "old.schema.json").write_text("{}", encoding="utf-8")

    write_json_schemas(tmp_path)

    assert (tmp_path / "club.schema.json").is_file()
    assert not (tmp_path / "old.schema.json").exists()


def test_the_export_command_writes_to_the_given_directory(tmp_path: Path) -> None:
    assert main(["--out", str(tmp_path)]) == 0

    assert (tmp_path / "season.schema.json").is_file()
