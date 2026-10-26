"""Composition root: the only place that wires ports to adapters (PLAN §3.2).

It is the only module allowed to import `mister.*.infrastructure`.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import sqlalchemy as sa

from mister.catalog.application.load_catalog import LoadCatalog
from mister.catalog.application.load_types import CatalogLoadUnavailableError
from mister.catalog.application.ratings_tool import RatingsTool
from mister.catalog.application.validate_content import ValidateContent
from mister.catalog.infrastructure.content_schema.rating_sheets import YamlRatingSheetStore
from mister.catalog.infrastructure.sqlalchemy.publisher import SqlCatalogPublisher
from mister.catalog.infrastructure.yaml_validation import YamlContentValidator
from mister.settings import Settings


@dataclass(frozen=True, slots=True)
class Container:
    settings: Settings


def bootstrap(settings: Settings | None = None) -> Container:
    return Container(settings=settings if settings is not None else Settings())


def build_ratings_tool(content_root: Path) -> RatingsTool:
    """The ratings use case over the YAML content under `content_root` (used by the CLI)."""
    return RatingsTool(YamlRatingSheetStore(content_root))


def build_validate_content(content_root: Path) -> ValidateContent:
    """Wire the content validation use case to the root-bound YAML adapter."""
    return ValidateContent(YamlContentValidator(content_root))


@contextmanager
def build_load_catalog(database_url: str | None = None) -> Iterator[LoadCatalog]:
    """Wire the SQL publisher for one command and release its engine afterwards."""
    url = database_url if database_url is not None else Settings().database_url
    try:
        engine = sa.create_engine(url)
    except sa.exc.SQLAlchemyError as error:
        raise CatalogLoadUnavailableError(f"database configuration unavailable: {error}") from error
    try:
        yield LoadCatalog(SqlCatalogPublisher(engine))
    finally:
        engine.dispose()
