"""Atomic PostgreSQL snapshots of release-validated playable seasons."""

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import cast

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from mister.catalog.application.api import (
    PlayableSeasonDTO,
    PlayableSeasonNotFoundError,
    PlayableSeasonSummaryDTO,
)
from mister.catalog.infrastructure.sqlalchemy.codec import JsonValue, decode_season, encode_season
from mister.catalog.infrastructure.yaml_loader import YamlSeasonContentProvider
from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import PlayableSeasonId

metadata = sa.MetaData()
catalog_version = sa.Table(
    "catalog_version",
    metadata,
    sa.Column("id", sa.SmallInteger, primary_key=True),
    sa.Column("content_hash", sa.String(64), nullable=False),
)
catalog_seasons = sa.Table(
    "catalog_seasons",
    metadata,
    sa.Column("id", sa.String(64), primary_key=True),
    sa.Column("content_hash", sa.String(64), nullable=False),
    sa.Column("payload", JSONB, nullable=False),
)


@dataclass(frozen=True, slots=True)
class CatalogLoadResult:
    content_hash: str
    season_count: int
    changed: bool


def _content_hash(root: Path) -> str:
    """Hash paths and bytes of the complete YAML tree, including historical sources."""
    if not root.is_dir():
        raise InvalidValueError(f"content root {root} is not a directory")
    digest = sha256()
    for path in sorted(root.rglob("*.yaml")):
        if not path.is_file():
            continue
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


class SqlCatalogLoader:
    """Replace the whole published catalog in one transaction when content changes."""

    def __init__(self, engine: sa.Engine) -> None:
        self._engine = engine

    def load(self, root: Path) -> CatalogLoadResult:
        """Publish a release tree; a matching hash performs no database writes."""
        before = _content_hash(root)
        yaml_provider = YamlSeasonContentProvider(root)
        summaries = yaml_provider.list_playable_seasons()
        if not summaries:
            raise InvalidValueError("cannot publish a catalog with zero playable seasons")
        seasons = tuple(yaml_provider.get_playable_season(summary.id) for summary in summaries)
        payloads = tuple((season.id.value, encode_season(season)) for season in seasons)
        if _content_hash(root) != before:
            raise InvalidValueError("content changed during catalog loading")

        with self._engine.begin() as connection:
            current = connection.scalar(
                sa.select(catalog_version.c.content_hash)
                .where(catalog_version.c.id == 1)
                .with_for_update()
            )
            if current is None:
                raise InvalidValueError("catalog migration has not initialized its version row")
            if current == before:
                return CatalogLoadResult(before, len(seasons), changed=False)
            connection.execute(sa.delete(catalog_seasons))
            connection.execute(
                sa.insert(catalog_seasons),
                [
                    {"id": season_id, "content_hash": before, "payload": payload}
                    for season_id, payload in payloads
                ],
            )
            connection.execute(
                sa.update(catalog_version)
                .where(catalog_version.c.id == 1)
                .values(content_hash=before)
            )
        return CatalogLoadResult(before, len(seasons), changed=True)


class SqlSeasonContentProvider:
    """Read immutable published seasons from the currently loaded SQL snapshot."""

    def __init__(self, engine: sa.Engine) -> None:
        self._engine = engine

    def list_playable_seasons(self) -> tuple[PlayableSeasonSummaryDTO, ...]:
        with self._engine.connect() as connection:
            payloads = connection.execute(
                sa.select(catalog_seasons.c.payload).order_by(catalog_seasons.c.id)
            ).scalars()
            return tuple(
                decode_season(cast("dict[str, JsonValue]", payload)).summary()
                for payload in payloads
            )

    def get_playable_season(self, season_id: PlayableSeasonId) -> PlayableSeasonDTO:
        with self._engine.connect() as connection:
            payload = connection.scalar(
                sa.select(catalog_seasons.c.payload).where(catalog_seasons.c.id == season_id.value)
            )
        if payload is None:
            raise PlayableSeasonNotFoundError(season_id)
        return decode_season(cast("dict[str, JsonValue]", payload))
