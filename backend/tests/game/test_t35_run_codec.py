from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, Literal
from uuid import UUID

import pytest

from mister.game.application import run_codec
from mister.game.application.run_codec import (
    RunCodec,
    assert_format1_schema_supported,
    decode_run,
    encode_run,
)
from mister.game.domain.board import GoalKind
from mister.game.domain.run import (
    BlockDefinition,
    BlockResolution,
    ClosureOutcome,
    DecisionOption,
    DilemmaDefinition,
    Run,
    RunStatus,
)
from mister.game.domain.squad_registry import Membership, SquadRegistry, SquadTransfer
from mister.game.domain.state import (
    CompetitionPriority,
    ForcedInjury,
    PlayerState,
    Position,
    Priority,
    RunState,
    Tactic,
    TacticStyle,
)
from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import (
    BlockId,
    ClubSeasonId,
    CompetitionId,
    DilemmaId,
    OptionId,
    PlayableSeasonId,
    PlayerId,
    RunId,
)
from mister.shared_kernel.seed import Seed


def make_run() -> Run:
    club = ClubSeasonId("test-fc-2000-01")
    rival = ClubSeasonId("rival-fc-2000-01")
    player = PlayerId("keeper")
    state = RunState(
        club,
        SquadRegistry(
            (Membership(player, club),), (SquadTransfer(player, club, rival, date(2000, 2, 1)),)
        ),
        (PlayerState(player, Position.GK, 80, 30, 50, 90, date(2000, 3, 1), True, 4),),
        Tactic(TacticStyle.BALANCED, (4, 3, 3)),
        (CompetitionPriority(CompetitionId("liga-test"), Priority.HIGH),),
        60,
        55,
        date(2000, 2, 1),
        (ForcedInjury(player, date(2000, 2, 2), 3),),
    )
    blocks = (
        BlockDefinition(
            BlockId("opening"),
            (DilemmaDefinition(DilemmaId("captain"), (DecisionOption(OptionId("keep")),)),),
        ),
        BlockDefinition(BlockId("closing"), ()),
    )
    now = datetime(2000, 1, 1, tzinfo=UTC)
    run = Run.start(
        RunId(UUID(int=1)), PlayableSeasonId("test-fc-2000-01"), Seed(7), state, blocks, now
    )[0]
    run = run.take_decision(DilemmaId("captain"), OptionId("keep"), now)[0]
    return run.advance_block(
        BlockResolution(BlockId("opening"), state, b"\x00opaque\xff", cursor=date(2000, 2, 1)), now
    )[0]


def test_run_codec_round_trips_full_state_registry_decisions_cursor_and_opaque_payload() -> None:
    run = make_run()
    encoded = RunCodec.encode(run)
    decoded = RunCodec.decode(encoded)
    assert decoded == run
    assert decoded.block_records[0].payload == b"\x00opaque\xff"
    assert decoded.cursor == date(2000, 2, 1)
    assert decoded.run_state.squad_registry.transfers[0].to_club_season_id == ClubSeasonId(
        "rival-fc-2000-01"
    )
    assert decode_run(encode_run(run)) == run


@pytest.mark.parametrize(
    "payload", [b"{}", b'{"format_version":99}', b'{"format_version":1,"run":{}}']
)
def test_run_codec_rejects_unknown_or_incomplete_formats(payload: bytes) -> None:
    with pytest.raises(InvalidValueError):
        RunCodec.decode(payload)


def test_run_codec_rejects_non_mapping_input() -> None:
    with pytest.raises(InvalidValueError):
        RunCodec.decode(b'{ "format_version": 1 }')


def test_run_codec_rejects_unknown_tags_and_missing_fields() -> None:
    encoded = RunCodec.encode(make_run())
    encoded["aggregate"] = {"$unknown": True}
    with pytest.raises(InvalidValueError):
        RunCodec.decode(encoded)


def test_run_codec_rejects_values_with_wrong_types() -> None:
    encoded = RunCodec.encode(make_run())
    aggregate = encoded["aggregate"]
    assert isinstance(aggregate, dict)
    run_fields = aggregate["fields"]
    assert isinstance(run_fields, dict)
    state = run_fields["run_state"]
    assert isinstance(state, dict)
    state_fields = state["fields"]
    assert isinstance(state_fields, dict)
    state_fields["team_morale"] = True
    with pytest.raises(InvalidValueError, match="field types"):
        RunCodec.decode(encoded)
    encoded = RunCodec.encode(make_run())
    aggregate = encoded["aggregate"]
    assert isinstance(aggregate, dict)
    aggregate["fields"] = {}
    with pytest.raises(InvalidValueError):
        RunCodec.decode(encoded)


def test_run_codec_schema_is_frozen_for_format_one() -> None:
    assert_format1_schema_supported()


def test_run_codec_round_trips_sacked_and_finished_terminal_states() -> None:
    run = make_run()
    first = run.blocks[run.block_index]
    sacked = run.advance_block(
        BlockResolution(first.id, run.run_state, b"sacked", ClosureOutcome.SACKED),
        datetime(2000, 1, 2, tzinfo=UTC),
    )[0]
    assert sacked.status is RunStatus.SACKED
    assert RunCodec.decode(RunCodec.encode(sacked)) == sacked
    finished = run.advance_block(
        BlockResolution(first.id, run.run_state, b"finished"), datetime(2000, 1, 3, tzinfo=UTC)
    )[0]
    assert finished.status is RunStatus.FINISHED
    assert RunCodec.decode(RunCodec.encode(finished)) == finished


@pytest.mark.parametrize("value", [["raw"], 1.5, object()])
def test_run_codec_rejects_values_without_a_tagged_json_representation(value: object) -> None:
    with pytest.raises(InvalidValueError):
        run_codec._decode(value)


@pytest.mark.parametrize(
    "value",
    [
        {"$bytes": None},
        {"$bytes": "YQ==="},
        {"$bytes": "YR=="},
        {"$date": 20000101},
        {"$date": "20000101"},
        {"$date": "not-a-date"},
        {"$datetime": "2000-01-01 00:00:00"},
        {"$datetime": "not-a-datetime"},
        {"$uuid": "00000000-0000-0000-0000-00000000000A"},
        {"$uuid": "not-a-uuid"},
        {"$tuple": 1},
    ],
)
def test_run_codec_rejects_invalid_or_noncanonical_scalar_tags(value: object) -> None:
    with pytest.raises(InvalidValueError):
        run_codec._decode(value)


@pytest.mark.parametrize(
    "value",
    [
        {"$enum": "unknown.Enum", "value": "x"},
        {"$enum": "builtins.str", "value": "x"},
        {"$enum": "mister.game.domain.run.RunStatus", "value": "unknown"},
        {"$type": "unknown.Value", "fields": {}},
        {"$type": "mister.game.domain.run.RunStatus", "fields": {}},
        {"$type": "mister.game.domain.run.Run", "fields": []},
        {"$type": "mister.game.domain.run.Run", "fields": {"extra": None}},
        {"$unknown": True},
    ],
)
def test_run_codec_rejects_unknown_tags_and_schema_drift(value: object) -> None:
    with pytest.raises(InvalidValueError):
        run_codec._decode(value)


def test_run_codec_rejects_a_known_enum_with_an_unknown_value() -> None:
    with pytest.raises(InvalidValueError, match="enum value"):
        run_codec._decode({"$enum": "mister.game.domain.run.RunStatus", "value": "unknown"})


def test_run_codec_rejects_non_run_values_and_wrong_envelopes() -> None:
    with pytest.raises(InvalidValueError, match="requires a Run"):
        RunCodec.encode(object())  # type: ignore[arg-type]
    with pytest.raises(InvalidValueError, match="envelope"):
        RunCodec.decode([])
    with pytest.raises(InvalidValueError, match="format"):
        RunCodec.decode({"format_version": True, "aggregate": {}})
    with pytest.raises(InvalidValueError, match="not a Run"):
        RunCodec.decode({"format_version": 1, "aggregate": None})


def test_run_codec_schema_drift_fails_before_encoding(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(run_codec, "_FORMAT1_SCHEMA_FINGERPRINT", "changed")

    with pytest.raises(InvalidValueError, match="schema changed"):
        RunCodec.encode(make_run())


def test_run_codec_encoder_rejects_values_outside_the_format_allowlist() -> None:
    with pytest.raises(InvalidValueError, match="unsupported run enum"):
        run_codec._encode(GoalKind.WIN)
    with pytest.raises(InvalidValueError, match="unsupported value"):
        run_codec._encode(object())


def test_run_codec_scalar_encoder_uses_stable_tags_for_supported_values() -> None:
    value = datetime(2000, 1, 1, tzinfo=UTC)
    assert run_codec._encode(value) == {"$datetime": value.isoformat()}
    assert run_codec._encode(date(2000, 1, 1)) == {"$date": "2000-01-01"}
    assert run_codec._decode({"$datetime": value.isoformat()}) == value
    assert run_codec._decode({"$date": "2000-01-01"}) == date(2000, 1, 1)

    @dataclass(frozen=True)
    class Unregistered:
        value: str

    with pytest.raises(InvalidValueError, match="unsupported run value"):
        run_codec._encode(Unregistered("x"))


def test_run_codec_type_matcher_distinguishes_bool_int_and_temporal_types() -> None:
    assert run_codec._matches(None, Any)
    assert run_codec._matches("anything", object)
    assert run_codec._matches(True, bool)
    assert not run_codec._matches(True, int)
    assert run_codec._matches((1, 2), tuple[int, ...])
    assert not run_codec._matches((1,), tuple[int, int])
    assert run_codec._matches(1, Literal[1])
    assert not run_codec._matches(True, Literal[1])
    assert run_codec._matches(date(2000, 1, 1), date)
    assert not run_codec._matches(datetime(2000, 1, 1), date)
    assert run_codec._matches(datetime(2000, 1, 1), datetime)
    assert run_codec._matches(Seed(3), Seed)
    assert not run_codec._matches("x", object())
