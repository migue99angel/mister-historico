"""Run replay inputs outlive catalog replacement and SQL adapter reconstruction."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from shutil import copytree
from typing import TYPE_CHECKING

import pytest
import sqlalchemy as sa
import yaml
from alembic import command
from alembic.config import Config
from testcontainers.community.postgres import PostgresContainer
from tests.contracts.suites.expected_test_fc import CONTENT_ROOT, TEST_FC_SEASON
from tests.contracts.suites.game_samples import REPLAY_INPUTS, make_run_record, next_version

from mister.catalog.infrastructure.sqlalchemy.catalog import (
    SqlCatalogLoader,
    SqlSeasonContentProvider,
)
from mister.game.infrastructure.catalog_adapter import CatalogRunContentAdapter
from mister.game.infrastructure.sqlalchemy.runs import SqlRunRepository
from mister.shared_kernel.errors import InvalidValueError

if TYPE_CHECKING:
    from collections.abc import Iterator

    from mister.game.application.ports import RunRepository

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


def test_replay_bytes_survive_catalog_replacement_and_removal(
    engine: sa.Engine, tmp_path: Path
) -> None:
    provider = SqlSeasonContentProvider(engine)
    SqlCatalogLoader(engine).load(CONTENT_ROOT)
    snapshot_a = CatalogRunContentAdapter(provider).capture(TEST_FC_SEASON)
    record = replace(
        make_run_record(),
        replay_inputs=replace(REPLAY_INPUTS, content=snapshot_a),
    )
    repo: RunRepository = SqlRunRepository(engine)
    repo.add(record)

    # Publish a different synthetic Test FC, changing a field the snapshot retains.
    changed_root = tmp_path / "content-b"
    copytree(CONTENT_ROOT, changed_root)
    squad_path = changed_root / "club-seasons" / "test-fc-2000-01" / "squad.yaml"
    squad = yaml.safe_load(squad_path.read_text())
    player = next(entry for entry in squad["players"] if entry["player_id"] == "tfc-03")
    player["rating"] = 75
    player["rating_override"]["value"] = 75
    squad_path.write_text(yaml.safe_dump(squad, sort_keys=False, allow_unicode=True))
    SqlCatalogLoader(engine).load(changed_root)
    captured_b = CatalogRunContentAdapter(SqlSeasonContentProvider(engine)).capture(TEST_FC_SEASON)
    assert captured_b.digest != snapshot_a.digest

    # Removing the current publication still leaves each run's original inputs intact.
    with engine.begin() as connection:
        connection.execute(sa.text("DELETE FROM catalog_seasons"))

    # Recreate persistence/catalog providers after publication removal.
    recreated = SqlRunRepository(engine)
    stored = recreated.get(record.run_id)

    assert stored is not None
    assert stored.replay_inputs == record.replay_inputs
    assert stored.replay_inputs.content.content_json.encode("utf-8") == (
        snapshot_a.content_json.encode("utf-8")
    )
    restored_a = CatalogRunContentAdapter.restore(stored.replay_inputs.content)
    player_a = next(
        player
        for player in restored_a.own_club_season.squad or ()
        if player.player_id.value == "tfc-03"
    )
    assert player_a.rating == 76
    assert stored.replay_inputs.engine_revision == "engine-1"
    assert stored.replay_inputs.rules_revision == "rules-1"
    assert stored.replay_inputs.initial_state_json == "{}"
    assert stored.replay_inputs.rules_configuration_json == "{}"

    altered_inputs = replace(stored.replay_inputs, initial_state_json='{"different":true}')
    with pytest.raises(InvalidValueError, match="immutable"):
        recreated.save(
            replace(next_version(stored), replay_inputs=altered_inputs),
            expected_version=stored.version,
        )
    assert recreated.get(record.run_id) == stored
