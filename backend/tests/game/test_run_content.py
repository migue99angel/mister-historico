"""Contracts for immutable, recoverable run inputs."""

from dataclasses import FrozenInstanceError, replace

import pytest

from mister.game.application.run_content import RunContentSnapshot
from mister.game.application.replay_inputs import ReplayInputs
from mister.game.infrastructure.run_content_codec import (
    decode_playable_season,
    encode_playable_season,
)
from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import PlayableSeasonId
from tests.contracts.suites.expected_test_fc import build_expected_test_fc_season


def _inputs(snapshot: RunContentSnapshot) -> ReplayInputs:
    return ReplayInputs(
        content=snapshot,
        initial_state_json='{"morale":50}',
        rules_configuration_json='{"version":1}',
        engine_revision="engine-1",
        rules_revision="rules-1",
    )


def test_codec_round_trips_the_complete_test_fc_dto() -> None:
    season = build_expected_test_fc_season()

    snapshot = encode_playable_season(season)

    assert decode_playable_season(snapshot) == season
    assert snapshot.playable_season_id == season.id


def test_snapshot_digest_covers_exact_canonical_content_bytes() -> None:
    season = build_expected_test_fc_season()

    snapshot = encode_playable_season(season)

    assert snapshot.digest
    with pytest.raises(FrozenInstanceError):
        snapshot.content_json = "{}"  # type: ignore[misc]


def test_snapshot_envelope_cannot_claim_another_season() -> None:
    snapshot = encode_playable_season(build_expected_test_fc_season())

    with pytest.raises(InvalidValueError, match="identity"):
        decode_playable_season(
            replace(snapshot, playable_season_id=PlayableSeasonId("another-season"))
        )


def test_replay_json_must_be_canonical_objects_and_revisions_nonempty() -> None:
    snapshot = encode_playable_season(build_expected_test_fc_season())

    with pytest.raises(InvalidValueError):
        ReplayInputs(snapshot, '{"b":2, "a":1}', "{}", "engine-1", "rules-1")
    with pytest.raises(InvalidValueError):
        ReplayInputs(snapshot, "[]", "{}", "engine-1", "rules-1")
    with pytest.raises(InvalidValueError, match="revision"):
        ReplayInputs(snapshot, "{}", "{}", " ", "rules-1")

