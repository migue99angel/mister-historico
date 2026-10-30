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
from mister.shared_kernel.ids import PlayerId


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
    reloaded = adapter.present_run(
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
