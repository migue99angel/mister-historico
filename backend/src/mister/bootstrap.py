"""Composition root: the only place that wires ports to adapters (PLAN §3.2).

It is the only module allowed to import `mister.*.infrastructure`.
"""

from dataclasses import dataclass
from pathlib import Path

from mister.catalog.application.ratings_tool import RatingsTool
from mister.catalog.infrastructure.content_schema.rating_sheets import YamlRatingSheetStore
from mister.settings import Settings


@dataclass(frozen=True, slots=True)
class Container:
    settings: Settings


def bootstrap(settings: Settings | None = None) -> Container:
    return Container(settings=settings if settings is not None else Settings())


def build_ratings_tool(content_root: Path) -> RatingsTool:
    """The ratings use case over the YAML content under `content_root` (used by the CLI)."""
    return RatingsTool(YamlRatingSheetStore(content_root))
