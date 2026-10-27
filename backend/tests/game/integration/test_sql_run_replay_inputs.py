"""Run replay inputs outlive catalog replacement and SQL adapter reconstruction."""

from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from testcontainers.community.postgres import PostgresContainer

from mister.game.application.ports import RunRepository
from mister.game.infrastructure.sqlalchemy.runs import SqlRunRepository
from mister.shared_kernel.errors import InvalidValueError
from tests.contracts.suites.game_samples import REPLAY_INPUTS, make_run_record, next_version

pytestmark = pytest.mark.integration
ALEMBIC_INI = Path(__file__).resolve().parents[3] / "alembic.ini"


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


def test_replay_bytes_survive_catalog_removal_and_repository_recreation(
    engine: sa.Engine,
) -> None:
    record = make_run_record()
    repo: RunRepository = SqlRunRepository(engine)
    repo.add(record)

    # Catalog publication can be deleted or replaced independently of a run.
    with engine.begin() as connection:
        connection.execute(sa.text("DELETE FROM catalog_seasons"))

    recreated = SqlRunRepository(engine)
    stored = recreated.get(record.run_id)

    assert stored is not None
    assert stored.replay_inputs == REPLAY_INPUTS
    assert stored.replay_inputs.content.content_json.encode("utf-8") == (
        REPLAY_INPUTS.content.content_json.encode("utf-8")
    )

    altered_inputs = replace(REPLAY_INPUTS, initial_state_json='{"different":true}')
    with pytest.raises(InvalidValueError, match="immutable"):
        recreated.save(
            replace(next_version(stored), replay_inputs=altered_inputs),
            expected_version=stored.version,
        )
    assert recreated.get(record.run_id) == stored
