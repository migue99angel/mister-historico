"""Contracts for immutable, recoverable run inputs."""

from dataclasses import FrozenInstanceError, replace
import hashlib
import json

import pytest

from mister.game.application.run_content import RunContentSnapshot
from mister.game.application.replay_inputs import ReplayInputs
from mister.game.infrastructure.run_content_codec import (
    decode_playable_season,
    encode_playable_season,
)
from mister.game.infrastructure.catalog_adapter import CatalogRunContentAdapter
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


def test_capture_reads_once_and_restore_survives_a_catalog_republication() -> None:
    season_a = build_expected_test_fc_season()

    class Provider:
        season = season_a
        calls = 0
        available = True

        def get_playable_season(self, season_id: PlayableSeasonId):
            self.calls += 1
            if not self.available:
                raise AssertionError("restoration consulted the live catalog")
            assert season_id == self.season.id
            return self.season

    provider = Provider()
    adapter = CatalogRunContentAdapter(provider)  # type: ignore[arg-type]
    snapshot_a = adapter.capture(season_a.id)
    assert provider.calls == 1

    provider.season = replace(season_a, manager=replace(season_a.manager, display_name="Updated manager"))
    snapshot_b = adapter.capture(season_a.id)
    provider.available = False
    restored_a = adapter.restore(snapshot_a)

    assert provider.calls == 2
    assert restored_a == season_a
    assert adapter.restore(snapshot_b).manager.display_name == "Updated manager"
    assert snapshot_a.content_json != snapshot_b.content_json


def test_unknown_codec_tags_and_fields_are_rejected() -> None:
    snapshot = encode_playable_season(build_expected_test_fc_season())
    unknown_tag_json = snapshot.content_json.replace('"$type":"TacticDTO"', '"$type":"FutureTacticDTO"', 1)
    unknown_tag = replace(snapshot, content_json=unknown_tag_json, digest=hashlib.sha256(unknown_tag_json.encode()).hexdigest())

    with pytest.raises(InvalidValueError, match="unknown DTO tag"):
        decode_playable_season(unknown_tag)

    raw = json.loads(snapshot.content_json)
    raw["fields"]["future_field"] = True
    fields_json = json.dumps(raw, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    with pytest.raises(InvalidValueError, match="fields do not match"):
        decode_playable_season(replace(snapshot, content_json=fields_json, digest=hashlib.sha256(fields_json.encode()).hexdigest()))


def test_supported_replay_revisions_are_explicit() -> None:
    replay = _inputs(encode_playable_season(build_expected_test_fc_season()))

    replay.ensure_compatible(engine_revisions={"engine-1"}, rules_revisions={"rules-1"})
    with pytest.raises(InvalidValueError, match="not supported"):
        replay.ensure_compatible(engine_revisions={"engine-2"}, rules_revisions={"rules-1"})


@pytest.mark.parametrize("format_version", [True, 1.0, "1"])
def test_format_version_must_be_an_integer_not_an_equal_value(format_version: object) -> None:
    snapshot = encode_playable_season(build_expected_test_fc_season())

    with pytest.raises(InvalidValueError, match="format"):
        replace(snapshot, format_version=format_version)  # type: ignore[arg-type]


@pytest.mark.parametrize("content", ["[]", "{\"x\":1}", "{\"$type\":\"PlayableSeasonDTO\",\"fields\":{},\"fields\":{}}", "{\"$type\":\"PlayableSeasonDTO\",\"fields\":{},\"x\":1}"])
def test_snapshot_envelope_rejects_noncanonical_or_arbitrary_json(content: str) -> None:
    with pytest.raises(InvalidValueError):
        RunContentSnapshot(1, content, hashlib.sha256(content.encode()).hexdigest(), PlayableSeasonId("test-fc-2000-01"))


@pytest.mark.parametrize("revision", [0, None, " "])
def test_replay_revisions_must_be_nonempty_strings(revision: object) -> None:
    snapshot = encode_playable_season(build_expected_test_fc_season())

    with pytest.raises(InvalidValueError, match="revision"):
        ReplayInputs(snapshot, "{}", "{}", revision, "rules-1")  # type: ignore[arg-type]

