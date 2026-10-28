"""Real in-memory Game API lifecycle through the deterministic simulation engine."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol, cast

from tests.game.test_t35_use_cases import _setup

from mister.game.application.api import GameApi
from mister.game.application.rules import RulesConfiguration
from mister.game.application.use_cases import AdvanceBlock
from mister.game.infrastructure.catalog_adapter import CatalogRunContentAdapter
from mister.game.infrastructure.in_memory.run_repository import InMemoryUnitOfWork
from mister.game.infrastructure.presentation_adapter import CatalogPresentationAdapter
from mister.game.infrastructure.security.run_tokens import Sha256RunTokenHasher
from mister.game.infrastructure.simulation_adapter import SimulationServiceAdapter
from mister.settings import Settings
from mister.shared_kernel.clock import FixedClock
from mister.shared_kernel.events import InMemoryEventBus
from mister.shared_kernel.ids import PlayableSeasonId, RunId
from mister.simulation.application.api import SimulationService

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mister.catalog.application.api import (
        PlayableSeasonDTO,
        PlayableSeasonSummaryDTO,
        SeasonContentProvider,
    )


class _MutableProvider(Protocol):
    season: PlayableSeasonDTO


class _RetirableProvider:
    def __init__(self, provider: SeasonContentProvider) -> None:
        self._provider = provider
        self.retired = False

    def list_playable_seasons(self) -> Sequence[PlayableSeasonSummaryDTO]:
        if self.retired:
            raise AssertionError("retired Catalog was queried")
        return self._provider.list_playable_seasons()

    def get_playable_season(self, season_id: PlayableSeasonId) -> PlayableSeasonDTO:
        if self.retired:
            raise AssertionError(f"retired Catalog was queried for {season_id}")
        return self._provider.get_playable_season(season_id)


def _version(value: object) -> int:
    return cast("int", cast("dict[str, object]", value)["version"])


def _json_object(value: object) -> dict[str, object]:
    return cast("dict[str, object]", value)


def _json_list(value: object) -> list[dict[str, object]]:
    return cast("list[dict[str, object]]", value)


def _replace_live_catalog_with_b(provider: _MutableProvider, season: PlayableSeasonDTO) -> None:
    changed = replace(
        season,
        manager=replace(season.manager, display_name="Mister B", alias_name="Alias B"),
        club_seasons=tuple(
            replace(
                club,
                name=f"B {club.name}",
                squad=(
                    tuple(
                        replace(player, display_name=f"B {player.display_name}")
                        for player in club.squad
                    )
                    if club.squad is not None
                    else None
                ),
            )
            for club in season.club_seasons
        ),
        dilemmas=tuple(
            replace(
                dilemma,
                title=f"B {dilemma.title}",
                prompt=f"B {dilemma.prompt}",
                options=tuple(
                    replace(option, label=f"B {option.label}") for option in dilemma.options
                ),
            )
            for dilemma in season.dilemmas
        ),
        texts=tuple(replace(item, body=f"B {item.body}") for item in season.texts),
    )
    provider.season = changed


def test_game_api_replays_original_advance_after_a_later_real_block() -> None:  # noqa: PLR0915
    rules = RulesConfiguration.a_profile()
    rules = replace(rules, board=replace(rules.board, sacking_threshold=0))
    season, provider, store, _, start, get, take = _setup(rules)
    hasher = Sha256RunTokenHasher()
    uow = InMemoryUnitOfWork(store)
    simulator = SimulationServiceAdapter(SimulationService())
    advance = AdvanceBlock(
        uow=uow,
        clock=FixedClock(datetime(2026, 10, 28, tzinfo=UTC)),
        event_bus=InMemoryEventBus(),
        token_hasher=hasher,
        restore_game=CatalogRunContentAdapter.restore_game,
        simulator=simulator,
    )
    retirable_provider = _RetirableProvider(provider)
    presentation = CatalogPresentationAdapter(retirable_provider, Settings())
    api = GameApi(
        start_run=start,
        get_run=get,
        take_decision=take,
        advance_block=advance,
        uow=uow,
        token_hasher=hasher,
        presentation=presentation,
        seasons=presentation,
    )

    started = api.start_run(season.id)
    assert set(started.to_json()) == {"runToken", "run"}
    run_id = RunId.parse(str(started.view.to_json()["runId"]))
    _replace_live_catalog_with_b(provider, season)
    assert api.get_season(season.id).to_json()["historicalManager"] == "Mister B"
    retirable_provider.retired = True

    current = api.get_run(run_id, started.run_token)
    current_json = current.to_json()
    initial_dilemmas = _json_list(current_json["pendingDilemmas"])
    assert initial_dilemmas
    assert all(not str(item["title"]).startswith("B ") for item in initial_dilemmas)
    assert all(not str(item["prompt"]).startswith("B ") for item in initial_dilemmas)
    assert all(
        not str(option["label"]).startswith("B ")
        for dilemma in initial_dilemmas
        for option in _json_list(dilemma["options"])
    )
    assert all("effects" not in item for item in initial_dilemmas)
    assert all("historicalOption" not in item for item in initial_dilemmas)
    squad = _json_object(current_json["squad"])
    players = _json_list(squad["players"])
    assert all(not str(item["displayName"]).startswith("B ") for item in players)
    assert "seed" not in current_json
    assert "runToken" not in current_json
    first_block = season.blocks[0]
    first_decisions = [item for item in season.dilemmas if item.block_id == first_block.id]
    assert first_decisions
    first_choice_key = "decision-block-one-0001"
    first_choice_version = _version(current.to_json())
    first_choice = first_decisions[0]
    first_option = first_choice.options[0]
    current = api.take_decision(
        run_id,
        started.run_token,
        first_choice_key,
        first_choice_version,
        first_choice.id,
        first_option.id,
    )
    first_choice_response = current
    for index, dilemma in enumerate(first_decisions[1:], start=1):
        current = api.take_decision(
            run_id,
            started.run_token,
            f"decision-block-one-{index + 1:04}",
            _version(current.to_json()),
            dilemma.id,
            dilemma.options[0].id,
        )
    first_advance_version = _version(current.to_json())
    first_advance_key = "advance-block-one-0001"
    first_advance = api.advance_block(
        run_id,
        started.run_token,
        first_advance_key,
        first_advance_version,
    )
    first_advance_json = first_advance.to_json()
    first_summary = _json_object(first_advance_json["lastBlockSummary"])
    first_results = _json_list(first_summary["results"])
    assert first_summary["blockNumber"] == 1
    assert first_results
    assert all(
        not str(_json_object(item["home"])["name"]).startswith("B ") for item in first_results
    )
    assert all(
        not str(_json_object(item["away"])["name"]).startswith("B ") for item in first_results
    )

    current = first_advance
    second_block = season.blocks[1]
    second_decisions = [item for item in season.dilemmas if item.block_id == second_block.id]
    for index, dilemma in enumerate(second_decisions):
        current = api.take_decision(
            run_id,
            started.run_token,
            f"decision-block-two-{index:04}",
            _version(current.to_json()),
            dilemma.id,
            dilemma.options[0].id,
        )
    api.advance_block(
        run_id,
        started.run_token,
        "advance-block-two-0001",
        _version(current.to_json()),
    )

    original_choice_replay = api.take_decision(
        run_id,
        started.run_token,
        first_choice_key,
        first_choice_version,
        first_choice.id,
        first_option.id,
    )
    original_advance_replay = api.advance_block(
        run_id,
        started.run_token,
        first_advance_key,
        first_advance_version,
    )

    assert original_choice_replay.to_json() == first_choice_response.to_json()
    assert original_advance_replay.to_json() == first_advance_json
    assert first_advance_json["pendingDilemmas"]
    pending = _json_list(first_advance_json["pendingDilemmas"])
    assert all(not str(item["title"]).startswith("B ") for item in pending)
