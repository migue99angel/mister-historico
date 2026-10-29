"""T3.9 key starter presentation and published facade command."""

from dataclasses import replace
from typing import Any

import pytest
from tests.contracts.suites.expected_test_fc import build_expected_test_fc_season
from tests.game.test_t39_key_starter import SUPER_FINAL, _Game, _game, _Provider

from mister.entrypoints.api.schemas import RunView as RunViewSchema
from mister.game.application.api import (
    GameApi,
    InvalidKeyStarterError,
    KeyStarterAlreadySelectedError,
    RunAlreadyFinishedError,
)
from mister.game.application.use_cases import RunView
from mister.game.infrastructure.in_memory.run_repository import InMemoryUnitOfWork
from mister.game.infrastructure.presentation_adapter import CatalogPresentationAdapter
from mister.game.infrastructure.security.run_tokens import Sha256RunTokenHasher
from mister.settings import Settings
from mister.shared_kernel.ids import PlayerId


def _present(game: _Game, view: RunView | None = None) -> dict[str, Any]:
    adapter = CatalogPresentationAdapter(_Provider(build_expected_test_fc_season()), Settings())
    value = view or game.get.execute(game.run_id, game.token)
    content = game.store.runs[game.run_id].replay_inputs.content
    presented = adapter.present_run(value, content).to_json()
    RunViewSchema.model_validate(presented)
    return presented


def _api(game: _Game) -> GameApi:
    adapter = CatalogPresentationAdapter(_Provider(build_expected_test_fc_season()), Settings())
    return GameApi(
        start_run=game.start,
        get_run=game.get,
        take_decision=game.take,
        advance_block=game.advance,
        select_key_starter=game.select,
        uow=InMemoryUnitOfWork(game.store),
        token_hasher=Sha256RunTokenHasher(),
        presentation=adapter,
        seasons=adapter,
    )


def test_the_run_view_publishes_the_captured_offer_without_duplicates() -> None:
    game = _game()
    entry = game.entry()
    assert entry.offer is not None

    offer = _present(game)["keyStarter"]

    assert offer["blockId"] == "b1"
    assert offer["fixtureId"] == SUPER_FINAL.value
    assert offer["date"] == "2000-08-20"
    assert offer["projectedStarterIds"] == [p.value for p in entry.offer.projected_starter_ids]
    assert [p["id"] for p in offer["projectedStarters"]] == offer["projectedStarterIds"]
    assert [p["id"] for p in offer["candidates"]] == [p.value for p in entry.offer.candidate_ids]
    assert len(set(offer["projectedStarterIds"])) == 11
    assert len({p["id"] for p in offer["candidates"]}) == len(offer["candidates"])
    assert offer["selectedPlayerId"] is None
    assert offer["keyMatchLabel"] == "Partido clave"
    assert offer["opponent"]["isUser"] is False
    assert offer["competitionName"]
    assert offer["venue"] in {"home", "away", "neutral"}


def test_offer_players_keep_their_captured_entry_state() -> None:
    game = _game()
    view = game.get.execute(game.run_id, game.token)
    candidate = game.entry().players[-1]
    changed = tuple(
        replace(p, morale=0, fitness=1, rating=1) if p.player_id == candidate.player_id else p
        for p in view.run.run_state.players
    )
    altered = replace(
        view, run=replace(view.run, run_state=replace(view.run.run_state, players=changed))
    )

    shown = _present(game, altered)["keyStarter"]["candidates"][-1]

    assert (shown["rating"], shown["morale"], shown["fitness"]) == (
        candidate.rating,
        candidate.morale,
        candidate.fitness,
    )


def test_the_selection_and_then_the_actual_lineup_are_published() -> None:
    game = _game()
    candidate = game.entry().offer.candidate_ids[0]  # type: ignore[union-attr]
    game.choose(candidate)
    assert _present(game)["keyStarter"]["selectedPlayerId"] == candidate.value

    game.advance_block()

    presented = _present(game)
    assert "keyStarter" not in presented
    outcome = presented["lastBlockSummary"]["keyStarterOutcome"]
    assert outcome["playerId"] == candidate.value
    assert outcome["fixtureId"] == SUPER_FINAL.value
    assert len(set(outcome["starterIds"])) == len(outcome["starterIds"]) == 11
    assert (candidate.value in outcome["starterIds"]) == (outcome["absenceReason"] is None)


def test_an_omitted_offer_publishes_no_evidence() -> None:
    game = _game()
    game.advance_block()

    assert "keyStarterOutcome" not in _present(game)["lastBlockSummary"]


def test_legacy_runs_publish_no_interaction() -> None:
    game = _game(offers=False)

    assert "keyStarter" not in _present(game)


def test_the_facade_selects_and_presents_the_run() -> None:
    game = _game()
    candidate = game.entry().offer.candidate_ids[0]  # type: ignore[union-attr]

    presented = _api(game).select_key_starter(
        game.run_id, game.token, "select-001", 0, SUPER_FINAL, candidate
    )

    assert presented.to_json()["keyStarter"]["selectedPlayerId"] == candidate.value
    assert presented.to_json()["version"] == 1


def test_the_facade_keeps_public_error_codes() -> None:
    game = _game()
    api = _api(game)
    first, second = game.entry().offer.candidate_ids[:2]  # type: ignore[union-attr]

    with pytest.raises(InvalidKeyStarterError):
        api.select_key_starter(game.run_id, game.token, "select-000", 0, SUPER_FINAL, PlayerId("x"))
    api.select_key_starter(game.run_id, game.token, "select-001", 0, SUPER_FINAL, first)
    with pytest.raises(KeyStarterAlreadySelectedError):
        api.select_key_starter(game.run_id, game.token, "select-002", 1, SUPER_FINAL, second)


def test_the_facade_reports_finished_runs() -> None:
    game = _game()
    for _ in range(5):
        game.advance_block()

    with pytest.raises(RunAlreadyFinishedError):
        _api(game).select_key_starter(
            game.run_id, game.token, "select-end", game.version(), SUPER_FINAL, PlayerId("x")
        )
