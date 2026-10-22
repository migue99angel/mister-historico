"""Alembic migrations apply cleanly on a real Postgres (testcontainers)."""

from collections.abc import Iterator
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from testcontainers.community.postgres import PostgresContainer

pytestmark = pytest.mark.integration

ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"


@pytest.fixture(scope="module")
def database_url() -> Iterator[str]:
    with PostgresContainer("postgres:16", driver="psycopg") as postgres:
        yield postgres.get_connection_url()


def test_upgrade_head_records_head_revision_in_alembic_version(
    database_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = Config(str(ALEMBIC_INI))

    command.upgrade(config, "head")

    head = ScriptDirectory.from_config(config).get_current_head()
    engine = sa.create_engine(database_url)
    try:
        with engine.connect() as connection:
            assert sa.inspect(connection).has_table("alembic_version")
            versions = (
                connection.execute(sa.text("SELECT version_num FROM alembic_version"))
                .scalars()
                .all()
            )
    finally:
        engine.dispose()
    assert head is not None
    assert versions == [head]
