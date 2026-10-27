"""Contracts for immutable, recoverable run inputs."""

import hashlib
import json
from dataclasses import FrozenInstanceError, replace

import pytest
from tests.contracts.suites.expected_test_fc import build_expected_test_fc_season

from mister.catalog.application.api import MoraleEffectDTO, PlayableSeasonDTO
from mister.game.application.replay_inputs import ReplayInputs
from mister.game.application.run_content import RunContentSnapshot
from mister.game.infrastructure.catalog_adapter import CatalogRunContentAdapter
from mister.game.infrastructure.run_content_codec import (
    assert_format1_schema_supported,
    decode_playable_season,
    encode_playable_season,
)
from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import PlayableSeasonId


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
    assert {
        type(effect).__name__
        for dilemma in season.dilemmas
        for option in dilemma.options
        for effect in option.effects
    } == {
        "BoardConfidenceEffectDTO",
        "CompetitionPriorityEffectDTO",
        "FitnessEffectDTO",
        "InjuryEffectDTO",
        "MoraleEffectDTO",
        "PlayerMoraleEffectDTO",
        "SellPlayerEffectDTO",
        "SetTacticEffectDTO",
        "SignPlayerEffectDTO",
        "YouthMinutesEffectDTO",
    }


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
    for invalid_json in ("{", '{"value":NaN}', '{"a":1,"a":2}'):
        with pytest.raises(InvalidValueError):
            ReplayInputs(snapshot, invalid_json, "{}", "engine-1", "rules-1")
    with pytest.raises(InvalidValueError):
        ReplayInputs(snapshot, "{}", "[]", "engine-1", "rules-1")
    with pytest.raises(InvalidValueError, match="revision"):
        ReplayInputs(snapshot, "{}", "{}", " ", "rules-1")


def test_capture_reads_once_and_restore_survives_a_catalog_republication() -> None:
    season_a = build_expected_test_fc_season()

    class Provider:
        season = season_a
        calls = 0
        available = True

        def get_playable_season(self, season_id: PlayableSeasonId) -> PlayableSeasonDTO:
            self.calls += 1
            if not self.available:
                raise AssertionError("restoration consulted the live catalog")
            assert season_id == self.season.id
            return self.season

    provider = Provider()
    adapter = CatalogRunContentAdapter(provider)  # type: ignore[arg-type]
    snapshot_a = adapter.capture(season_a.id)
    assert provider.calls == 1

    own_a = season_a.own_club_season
    assert own_a.squad is not None
    changed_squad = (replace(own_a.squad[0], rating=own_a.squad[0].rating + 1), *own_a.squad[1:])
    changed_clubs = tuple(
        replace(club, squad=changed_squad) if club.id == own_a.id else club
        for club in season_a.club_seasons
    )
    dilemma = season_a.dilemmas[0]
    option = dilemma.options[1]
    effect = option.effects[-1]
    assert isinstance(effect, MoraleEffectDTO)
    changed_effects = (*option.effects[:-1], replace(effect, delta=-1))
    changed_option = replace(option, effects=changed_effects)
    changed_dilemma = replace(
        dilemma,
        options=tuple(changed_option if item.id == option.id else item for item in dilemma.options),
    )
    provider.season = replace(
        season_a,
        manager=replace(season_a.manager, display_name="Updated manager"),
        club_seasons=changed_clubs,
        dilemmas=(changed_dilemma, *season_a.dilemmas[1:]),
    )
    snapshot_b = adapter.capture(season_a.id)
    provider.available = False
    restored_a = adapter.restore(snapshot_a)

    assert provider.calls == 2
    assert restored_a == season_a
    restored_b = adapter.restore(snapshot_b)
    assert restored_b.manager.display_name == "Updated manager"
    assert restored_b.own_club_season.squad is not None
    assert restored_b.own_club_season.squad[0].rating == own_a.squad[0].rating + 1
    restored_effect = restored_b.dilemmas[0].options[1].effects[-1]
    assert isinstance(restored_effect, MoraleEffectDTO)
    assert restored_effect.delta == -1
    assert snapshot_a.content_json != snapshot_b.content_json


def test_format_one_codec_gate_rejects_catalog_schema_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert_format1_schema_supported()
    monkeypatch.setitem(PlayableSeasonDTO.__annotations__, "season", int)

    with pytest.raises(InvalidValueError, match="format 1 schema"):
        encode_playable_season(build_expected_test_fc_season())


def test_unknown_codec_tags_and_fields_are_rejected() -> None:
    snapshot = encode_playable_season(build_expected_test_fc_season())
    unknown_tag_json = snapshot.content_json.replace(
        '"$type":"TacticDTO"', '"$type":"FutureTacticDTO"', 1
    )
    unknown_tag = replace(
        snapshot,
        content_json=unknown_tag_json,
        digest=hashlib.sha256(unknown_tag_json.encode()).hexdigest(),
    )

    with pytest.raises(InvalidValueError, match="unknown DTO tag"):
        decode_playable_season(unknown_tag)

    raw = json.loads(snapshot.content_json)
    raw["fields"]["future_field"] = True
    fields_json = json.dumps(
        raw, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )
    with pytest.raises(InvalidValueError, match="fields do not match"):
        decode_playable_season(
            replace(
                snapshot,
                content_json=fields_json,
                digest=hashlib.sha256(fields_json.encode()).hexdigest(),
            )
        )


@pytest.mark.parametrize("literal", [True, 1.0])
def test_format_one_literal_integer_fields_reject_equal_values_with_wrong_types(
    literal: object,
) -> None:
    snapshot = encode_playable_season(build_expected_test_fc_season())
    raw = json.loads(snapshot.content_json)

    def replace_knockout_leg(value: object) -> bool:
        if isinstance(value, dict):
            if value.get("$type") == "KnockoutSlotDTO":
                value["fields"]["leg"] = value["fields"].get("leg") or 1
                value["fields"]["leg"] = literal
                return True
            return any(replace_knockout_leg(child) for child in value.values())
        if isinstance(value, list):
            return any(replace_knockout_leg(child) for child in value)
        return False

    assert replace_knockout_leg(raw)
    content_json = json.dumps(raw, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    forged = replace(
        snapshot,
        content_json=content_json,
        digest=hashlib.sha256(content_json.encode()).hexdigest(),
    )

    with pytest.raises(InvalidValueError, match="literal"):
        decode_playable_season(forged)


def test_supported_replay_revisions_are_explicit() -> None:
    replay = _inputs(encode_playable_season(build_expected_test_fc_season()))

    replay.ensure_compatible(engine_revisions={"engine-1"}, rules_revisions={"rules-1"})
    with pytest.raises(InvalidValueError, match="not supported"):
        replay.ensure_compatible(engine_revisions={"engine-2"}, rules_revisions={"rules-1"})
    with pytest.raises(InvalidValueError, match="not supported"):
        replay.ensure_compatible(engine_revisions={"engine-1"}, rules_revisions={"rules-2"})


@pytest.mark.parametrize("format_version", [True, 1.0, "1"])
def test_format_version_must_be_an_integer_not_an_equal_value(format_version: object) -> None:
    snapshot = encode_playable_season(build_expected_test_fc_season())

    with pytest.raises(InvalidValueError, match="format"):
        replace(snapshot, format_version=format_version)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "content",
    [
        "[]",
        '{"x": 1}',
        '{"x":1,"x":2}',
    ],
)
def test_snapshot_envelope_rejects_nonobjects_duplicates_and_noncanonical_json(
    content: str,
) -> None:
    with pytest.raises(InvalidValueError):
        RunContentSnapshot(
            1,
            content,
            hashlib.sha256(content.encode()).hexdigest(),
            PlayableSeasonId("test-fc-2000-01"),
        )


def test_snapshot_envelope_stays_opaque_to_application_catalog_tags() -> None:
    opaque_json = '{"other":"tag"}'
    snapshot = RunContentSnapshot(
        1,
        opaque_json,
        hashlib.sha256(opaque_json.encode()).hexdigest(),
        PlayableSeasonId("test-fc-2000-01"),
    )

    with pytest.raises(InvalidValueError, match="unknown DTO tag"):
        decode_playable_season(snapshot)


def test_snapshot_envelope_requires_typed_identity_and_matching_digest() -> None:
    snapshot = encode_playable_season(build_expected_test_fc_season())
    with pytest.raises(InvalidValueError, match="identity"):
        replace(snapshot, playable_season_id="test-fc-2000-01")  # type: ignore[arg-type]
    with pytest.raises(InvalidValueError, match="digest"):
        replace(snapshot, digest="0" * 64)
    with pytest.raises(InvalidValueError, match="content_json"):
        replace(snapshot, content_json=1)  # type: ignore[arg-type]


@pytest.mark.parametrize("revision", [0, None, " "])
def test_replay_revisions_must_be_nonempty_strings(revision: object) -> None:
    snapshot = encode_playable_season(build_expected_test_fc_season())

    with pytest.raises(InvalidValueError, match="revision"):
        ReplayInputs(snapshot, "{}", "{}", revision, "rules-1")  # type: ignore[arg-type]


def test_replay_inputs_require_a_run_content_snapshot() -> None:
    with pytest.raises(InvalidValueError, match="snapshot"):
        ReplayInputs(None, "{}", "{}", "engine-1", "rules-1")  # type: ignore[arg-type]
