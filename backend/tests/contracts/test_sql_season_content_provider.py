"""SQL season provider contract and transactional YAML catalog loading."""

from collections.abc import Iterator
from pathlib import Path
from shutil import copytree

import pytest
import sqlalchemy as sa
import yaml
from alembic import command
from alembic.config import Config
from testcontainers.community.postgres import PostgresContainer

from mister.catalog.application.api import SeasonContentProvider
from mister.catalog.infrastructure.content_schema import ContentValidationError
from mister.catalog.infrastructure.sqlalchemy.catalog import (
    SqlCatalogLoader,
    SqlSeasonContentProvider,
)
from tests.contracts.suites.expected_test_fc import CONTENT_ROOT, TEST_FC_SEASON
from tests.contracts.suites.season_content_provider import SeasonContentProviderContract

pytestmark = pytest.mark.integration
ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"


@pytest.fixture(scope="module")
def engine() -> Iterator[sa.Engine]:
    with PostgresContainer("postgres:16.15", driver="psycopg") as postgres:
        url = postgres.get_connection_url()
        config = Config(str(ALEMBIC_INI))
        config.set_main_option("sqlalchemy.url", url)
        command.upgrade(config, "head")
        database = sa.create_engine(url)
        try:
            yield database
        finally:
            database.dispose()


@pytest.fixture(autouse=True)
def reset_catalog(engine: sa.Engine) -> None:
    with engine.begin() as connection:
        connection.execute(sa.text("DELETE FROM catalog_seasons"))
        connection.execute(sa.text("UPDATE catalog_version SET content_hash = '' WHERE id = 1"))


class TestSqlSeasonContentProvider(SeasonContentProviderContract):
    @pytest.fixture
    def provider(self, engine: sa.Engine) -> SeasonContentProvider:
        SqlCatalogLoader(engine).load(CONTENT_ROOT)
        return SqlSeasonContentProvider(engine)


def test_loading_the_same_content_twice_does_not_replace_rows(engine: sa.Engine) -> None:
    loader = SqlCatalogLoader(engine)

    first = loader.load(CONTENT_ROOT)
    with engine.connect() as connection:
        before = connection.scalar(sa.text("SELECT xmin FROM catalog_seasons"))
    second = loader.load(CONTENT_ROOT)

    assert first.changed is True
    assert second.changed is False
    assert second.content_hash == first.content_hash
    with engine.connect() as connection:
        assert connection.scalar(sa.text("SELECT count(*) FROM catalog_seasons")) == 1
        assert connection.scalar(sa.text("SELECT xmin FROM catalog_seasons")) == before


def _changed_rating_root(tmp_path: Path) -> Path:
    root = tmp_path / "content"
    copytree(CONTENT_ROOT, root)
    path = root / "club-seasons" / "test-fc-2000-01" / "squad.yaml"
    data = yaml.safe_load(path.read_text())
    player = next(entry for entry in data["players"] if entry["player_id"] == "tfc-03")
    player["rating"] = 75
    player["rating_override"]["value"] = 75
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    return root


def test_changing_a_rating_replaces_the_snapshot_and_hash(
    engine: sa.Engine, tmp_path: Path
) -> None:
    root = _changed_rating_root(tmp_path)
    loader = SqlCatalogLoader(engine)
    original = loader.load(CONTENT_ROOT)

    changed = loader.load(root)
    stored = SqlSeasonContentProvider(engine).get_playable_season(TEST_FC_SEASON)

    assert changed.changed is True
    assert changed.content_hash != original.content_hash
    assert (
        next(p for p in stored.own_club_season.squad or () if p.player_id.value == "tfc-03").rating
        == 75
    )


def test_invalid_release_does_not_replace_the_published_catalog(
    engine: sa.Engine, tmp_path: Path
) -> None:
    original = SqlCatalogLoader(engine).load(CONTENT_ROOT)
    root = tmp_path / "content"
    copytree(CONTENT_ROOT, root)
    path = root / "seasons" / "test-fc-2000-01" / "texts.yaml"
    path.write_text(path.read_text().replace("status: reviewed", "status: draft", 1))

    with pytest.raises(ContentValidationError):
        SqlCatalogLoader(engine).load(root)

    with engine.connect() as connection:
        assert connection.scalar(sa.text("SELECT content_hash FROM catalog_version")) == (
            original.content_hash
        )
    assert SqlSeasonContentProvider(engine).get_playable_season(TEST_FC_SEASON).summary().id == (
        TEST_FC_SEASON
    )


def test_database_error_rolls_back_deleted_rows(engine: sa.Engine, tmp_path: Path) -> None:
    original = SqlCatalogLoader(engine).load(CONTENT_ROOT)
    root = _changed_rating_root(tmp_path)

    def reject_insert(
        _connection: sa.Connection,
        _cursor: object,
        statement: str,
        _parameters: object,
        _context: object,
        _executemany: bool,
    ) -> None:
        if statement.startswith("INSERT INTO catalog_seasons"):
            raise RuntimeError("simulated insert failure")

    sa.event.listen(engine, "before_cursor_execute", reject_insert)
    try:
        with pytest.raises(RuntimeError, match="simulated insert failure"):
            SqlCatalogLoader(engine).load(root)
    finally:
        sa.event.remove(engine, "before_cursor_execute", reject_insert)

    with engine.connect() as connection:
        assert connection.scalar(sa.text("SELECT content_hash FROM catalog_version")) == (
            original.content_hash
        )
    stored = SqlSeasonContentProvider(engine).get_playable_season(TEST_FC_SEASON)
    player = next(p for p in stored.own_club_season.squad or () if p.player_id.value == "tfc-03")
    assert player.rating == 76
