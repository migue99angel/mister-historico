"""The PostgreSQL run adapter must satisfy the shared repository contract."""

from collections.abc import Iterator
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from testcontainers.community.postgres import PostgresContainer

from mister.game.application.ports import RunRepository
from mister.game.infrastructure.sqlalchemy.runs import SqlRunRepository
from tests.contracts.suites.run_repository import RepoFactory, RunRepositoryContract

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


class TestSqlRunRepository(RunRepositoryContract):
    @pytest.fixture
    def make_repo(self, engine: sa.Engine) -> RepoFactory:
        with engine.begin() as connection:
            connection.execute(sa.text("DELETE FROM runs"))

        def factory() -> RunRepository:
            return SqlRunRepository(engine)

        return factory
