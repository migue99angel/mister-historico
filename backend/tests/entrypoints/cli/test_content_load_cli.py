"""The content load command publishes Test FC through the wired SQL adapter."""

from collections.abc import Iterator
from pathlib import Path
from shutil import copytree

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from testcontainers.community.postgres import PostgresContainer
from typer.testing import CliRunner

from mister.entrypoints.cli.app import app

pytestmark = pytest.mark.integration
CONTENT_ROOT = Path(__file__).resolve().parents[2] / "fixtures" / "content"
ALEMBIC_INI = Path(__file__).resolve().parents[3] / "alembic.ini"
runner = CliRunner()


@pytest.fixture(scope="module")
def database_url() -> Iterator[str]:
    with PostgresContainer("postgres:16.15", driver="psycopg") as postgres:
        url = postgres.get_connection_url()
        config = Config(str(ALEMBIC_INI))
        config.set_main_option("sqlalchemy.url", url)
        command.upgrade(config, "head")
        yield url


def test_load_command_is_idempotent_and_reports_the_hash(
    database_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATABASE_URL", database_url)

    first = runner.invoke(app, ["content", "load", "--root", str(CONTENT_ROOT)])
    second = runner.invoke(app, ["content", "load", "--root", str(CONTENT_ROOT)])

    assert first.exit_code == 0, first.output
    assert "1 temporada" in first.output
    assert "hash" in first.output
    assert second.exit_code == 0, second.output
    assert "sin cambios" in second.output
    engine = sa.create_engine(database_url)
    try:
        with engine.connect() as connection:
            assert connection.scalar(sa.text("SELECT count(*) FROM catalog_seasons")) == 1
    finally:
        engine.dispose()


def test_invalid_release_content_exits_one_without_replacing_rows(
    database_url: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("DATABASE_URL", database_url)
    root = tmp_path / "content"
    copytree(CONTENT_ROOT, root)
    path = root / "seasons" / "test-fc-2000-01" / "texts.yaml"
    path.write_text(path.read_text().replace("status: reviewed", "status: draft", 1))

    result = runner.invoke(app, ["content", "load", "--root", str(root)])

    assert result.exit_code == 1
    assert "texts.yaml" in result.output
    engine = sa.create_engine(database_url)
    try:
        with engine.connect() as connection:
            assert connection.scalar(sa.text("SELECT count(*) FROM catalog_seasons")) == 1
    finally:
        engine.dispose()


def test_missing_root_exits_two(
    database_url: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("DATABASE_URL", database_url)

    result = runner.invoke(app, ["content", "load", "--root", str(tmp_path / "missing")])

    assert result.exit_code == 2
    assert "missing" in result.output
