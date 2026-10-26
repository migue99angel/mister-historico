"""SQL publisher satisfies the shared catalog publication contract on Postgres."""

from collections.abc import Iterator
from pathlib import Path
from shutil import copytree

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from testcontainers.community.postgres import PostgresContainer

from mister.catalog.application.load_types import CatalogLoadUnavailableError
from mister.catalog.application.ports import CatalogPublisher
from mister.catalog.infrastructure.sqlalchemy.publisher import SqlCatalogPublisher
from tests.contracts.suites.catalog_publisher import CatalogPublisherContract
from tests.contracts.suites.expected_test_fc import CONTENT_ROOT

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


class TestSqlCatalogPublisher(CatalogPublisherContract):
    @pytest.fixture
    def valid(self, engine: sa.Engine) -> tuple[CatalogPublisher, Path]:
        return SqlCatalogPublisher(engine), CONTENT_ROOT

    @pytest.fixture
    def invalid(self, engine: sa.Engine, tmp_path: Path) -> tuple[CatalogPublisher, Path]:
        root = tmp_path / "content"
        copytree(CONTENT_ROOT, root)
        path = root / "seasons" / "test-fc-2000-01" / "texts.yaml"
        path.write_text(path.read_text().replace("status: reviewed", "status: draft", 1))
        return SqlCatalogPublisher(engine), root

    @pytest.fixture
    def unavailable(self, engine: sa.Engine, tmp_path: Path) -> tuple[CatalogPublisher, Path]:
        return SqlCatalogPublisher(engine), tmp_path / "missing"


def test_missing_catalog_version_is_an_operational_error(engine: sa.Engine) -> None:
    with engine.begin() as connection:
        connection.execute(sa.text("DELETE FROM catalog_version"))
    try:
        with pytest.raises(CatalogLoadUnavailableError, match="version row"):
            SqlCatalogPublisher(engine).load(CONTENT_ROOT)
    finally:
        with engine.begin() as connection:
            connection.execute(
                sa.text("INSERT INTO catalog_version (id, content_hash) VALUES (1, '')")
            )
