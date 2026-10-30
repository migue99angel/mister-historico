"""Starter evidence resolves identities only from the run's captured content."""

from dataclasses import replace
from typing import Any

import pytest
from tests.contracts.suites.expected_test_fc import build_expected_test_fc_season
from tests.game.test_t39_key_starter import _game, _Provider
from tests.game.test_t39_key_starter_presentation import _present

from mister.entrypoints.api.schemas import RunView as RunViewSchema
from mister.game.application import ports
from mister.game.application.block_codec import decode_block
from mister.game.infrastructure.catalog_adapter import CatalogRunContentAdapter
from mister.game.infrastructure.presentation_adapter import CatalogPresentationAdapter
from mister.settings import Settings
from mister.shared_kernel.ids import DilemmaId, OptionId, PlayerId


@pytest.mark.parametrize("real_names", [False, True])
@pytest.mark.parametrize(
    "reason", [None, "injured", "not_in_squad", "youth_conflict", "fixture_not_played"]
)
def test_outcome_keeps_captured_names_for_every_participation_reason(
    reason: ports.StarterAbsenceReason | None, real_names: bool
) -> None:
    game = _game()
    offer = game.entry().offer
    assert offer is not None
    chosen = offer.candidate_ids[0]
    game.choose(chosen)
    game.advance_block()
    record = game.store.runs[game.run_id]
    season = build_expected_test_fc_season()
    players = {p.player_id: p for club in season.club_seasons for p in club.squad or ()}
    player = players[chosen]
    result = decode_block(game.snapshot().run.block_records[0].payload)
    actual = (
        ()
        if reason == "fixture_not_played"
        else (chosen,)
        if reason is None
        else (PlayerId("tfc-01"),)
    )
    result = replace(
        result,
        key_starter_outcome=ports.KeyStarterOutcome(
            offer.fixture_id, offer.date, chosen, actual, reason
        ),
    )
    adapter = CatalogPresentationAdapter(_UnavailableCatalog(), Settings(real_names=real_names))
    # Restore the original content rather than any current squad or Catalog publication.

    captured = CatalogRunContentAdapter.restore(record.replay_inputs.content)
    shown: dict[str, Any] = adapter._block_summary(
        result,
        None,
        1,
        captured,
        {c.id: c for c in captured.club_seasons},
        {c.id: c for c in captured.competitions},
        players,
    )
    outcome = shown["keyStarterOutcome"]
    assert outcome["selectedPlayer"] == {
        "id": chosen.value,
        "displayName": player.display_name if real_names else player.alias_name,
    }
    assert outcome["starters"] == [
        {
            "id": p.value,
            "displayName": players[p].display_name if real_names else players[p].alias_name,
        }
        for p in actual
    ]


class _UnavailableCatalog(_Provider):
    def __init__(self) -> None:
        super().__init__(build_expected_test_fc_season())

    def get_playable_season(self, season_id: Any) -> Any:
        raise AssertionError("presentation must use captured content")


def test_stored_evidence_gets_names_after_reload_replay_and_idempotent_advance() -> None:
    game = _game()
    offer = game.entry().offer
    assert offer is not None
    game.choose(offer.candidate_ids[0])
    game.decide_all()
    version = game.version()
    first = game.advance.execute(game.run_id, game.token, "identity-advance", version)
    before = _present(game)["lastBlockSummary"]["keyStarterOutcome"]
    retried = game.advance.execute(game.run_id, game.token, "identity-advance", version)
    assert retried == first
    assert game.replay.execute(game.run_id, game.token).verified
    adapter = CatalogPresentationAdapter(_UnavailableCatalog(), Settings())
    reloaded: dict[str, Any] = adapter.present_run(
        game.get.execute(game.run_id, game.token),
        game.store.runs[game.run_id].replay_inputs.content,
    ).to_json()
    after = reloaded["lastBlockSummary"]["keyStarterOutcome"]
    assert after == before
    assert after["selectedPlayer"]["id"] == offer.candidate_ids[0].value
    assert [p["id"] for p in after["starters"]] == after["starterIds"]
    RunViewSchema.model_validate(reloaded)
    # Old responses containing IDs only remain valid.
    del after["selectedPlayer"], after["starters"]
    RunViewSchema.model_validate(reloaded)


@pytest.mark.parametrize("unknown_starter", [False, True])
def test_missing_captured_identity_is_explicit_and_never_guessed(unknown_starter: bool) -> None:
    game = _game()
    game.advance_block()
    result = decode_block(game.snapshot().run.block_records[0].payload)
    actual = (PlayerId("tfc-01"), PlayerId("unknown")) if unknown_starter else (PlayerId("tfc-01"),)
    result = replace(
        result,
        key_starter_outcome=ports.KeyStarterOutcome(
            result.matches[0].fixture_id,
            result.matches[0].date,
            PlayerId("missing-player"),
            actual,
            "not_in_squad",
        ),
    )
    season = build_expected_test_fc_season()
    players = {p.player_id: p for club in season.club_seasons for p in club.squad or ()}
    adapter = CatalogPresentationAdapter(_UnavailableCatalog(), Settings())
    shown = adapter._block_summary(
        result,
        None,
        1,
        season,
        {c.id: c for c in season.club_seasons},
        {c.id: c for c in season.competitions},
        players,
    )
    outcome: Any = shown["keyStarterOutcome"]
    assert outcome["selectedPlayer"] is None
    if unknown_starter:
        assert outcome["starters"] is None
    else:
        assert outcome["starters"][0]["id"] == "tfc-01"


def test_sold_selected_player_retains_name_after_persistence_reload_and_replay() -> None:
    game = _game(seed_value=2000)
    game.take.execute(
        game.run_id, game.token, "counter-choice", game.version(), DilemmaId("d02"), OptionId("b")
    )
    game.advance_block()
    game.advance_block()
    offer = game.entry().offer
    assert offer is not None
    candidate = next(p for p in offer.candidate_ids if p.value in {"tfc-17", "tfc-18"})
    known = next(
        p for p in _present(game)["keyStarter"]["candidates"] if p["id"] == candidate.value
    )
    game.choose(candidate)
    option = "a" if candidate.value == "tfc-18" else "b"
    game.take.execute(
        game.run_id, game.token, "sale-choice", game.version(), DilemmaId("d05"), OptionId(option)
    )
    game.advance_block()
    reloaded = _present(game)
    assert candidate.value not in {p["id"] for p in reloaded["squad"]["players"]}
    outcome = reloaded["lastBlockSummary"]["keyStarterOutcome"]
    assert outcome["absenceReason"] == "not_in_squad"
    assert outcome["selectedPlayer"] == {"id": candidate.value, "displayName": known["displayName"]}
    assert game.replay.execute(game.run_id, game.token).verified
    assert _present(game)["lastBlockSummary"]["keyStarterOutcome"] == outcome
