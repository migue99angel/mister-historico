"""Export the content models as JSON Schema files (editor validation and documentation).

Regenerate the versioned schemas (`content/schema/*.schema.json`) after any model change:

    cd backend && uv run python -m mister.catalog.infrastructure.content_schema.export

A drift test fails when the versioned files differ from the models.
"""

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel

from mister.catalog.infrastructure.content_schema.club import ClubFile
from mister.catalog.infrastructure.content_schema.dilemmas import DilemmasFile
from mister.catalog.infrastructure.content_schema.fixtures import FixturesFile
from mister.catalog.infrastructure.content_schema.season import SeasonFile
from mister.catalog.infrastructure.content_schema.squad import AggregateFile, SquadFile
from mister.catalog.infrastructure.content_schema.standings import StandingsFile
from mister.catalog.infrastructure.content_schema.texts import TextsFile

JSON_SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"

SCHEMA_MODELS: dict[str, type[BaseModel]] = {
    "club": ClubFile,
    "squad": SquadFile,
    "aggregate": AggregateFile,
    "season": SeasonFile,
    "fixtures": FixturesFile,
    "standings": StandingsFile,
    "dilemmas": DilemmasFile,
    "texts": TextsFile,
}

# backend/src/mister/catalog/infrastructure/content_schema/export.py -> repository root
DEFAULT_OUTPUT_DIR = Path(__file__).parents[6] / "content" / "schema"


def render_json_schemas() -> dict[str, str]:
    """Return `{file name: JSON text}` for every content file type, deterministically."""
    rendered: dict[str, str] = {}
    for name, model in SCHEMA_MODELS.items():
        schema = {"$schema": JSON_SCHEMA_DIALECT, **model.model_json_schema()}
        rendered[f"{name}.schema.json"] = (
            json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        )
    return rendered


def write_json_schemas(output_dir: Path) -> list[Path]:
    """Write the schemas to `output_dir`, removing stale `*.schema.json` files."""
    rendered = render_json_schemas()
    output_dir.mkdir(parents=True, exist_ok=True)
    for stale in output_dir.glob("*.schema.json"):
        if stale.name not in rendered:
            stale.unlink()
    written: list[Path] = []
    for file_name, text in rendered.items():
        path = output_dir / file_name
        path.write_text(text, encoding="utf-8")
        written.append(path)
    return written


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export the content JSON Schemas.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT_DIR, help="output directory")
    arguments = parser.parse_args(argv)
    write_json_schemas(arguments.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
