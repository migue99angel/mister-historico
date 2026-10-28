from datetime import date, UTC, datetime
from uuid import UUID

import pytest

from mister.game.domain.run import BlockDefinition, BlockRecord, BlockResolution, DecisionOption, DilemmaDefinition, Run
from mister.game.domain.squad_registry import Membership, SquadRegistry, SquadTransfer
from mister.game.domain.state import CompetitionPriority, PlayerState, Position, Priority, RunState, Tactic, TacticStyle, ForcedInjury
from mister.game.application.run_codec import RunCodec
from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import BlockId, ClubSeasonId, CompetitionId, DilemmaId, OptionId, PlayableSeasonId, PlayerId, RunId
from mister.shared_kernel.seed import Seed


def make_run() -> Run:
    club = ClubSeasonId("test-fc-2000-01")
    rival = ClubSeasonId("rival-fc-2000-01")
    player = PlayerId("keeper")
    state = RunState(club, SquadRegistry((Membership(player, club),), (SquadTransfer(player, club, rival, date(2000, 2, 1)),)), (PlayerState(player, Position.GK, 80, 30, 50, 90, date(2000, 3, 1), True, 4),), Tactic(TacticStyle.BALANCED, (4, 3, 3)), (CompetitionPriority(CompetitionId("liga-test"), Priority.HIGH),), 60, 55, date(2000, 2, 1), (ForcedInjury(player, date(2000, 2, 2), 3),))
    blocks = (BlockDefinition(BlockId("opening"), (DilemmaDefinition(DilemmaId("captain"), (DecisionOption(OptionId("keep")),)),)), BlockDefinition(BlockId("closing"), ()))
    now = datetime(2000, 1, 1, tzinfo=UTC)
    run = Run.start(RunId(UUID(int=1)), PlayableSeasonId("test-fc-2000-01"), Seed(7), state, blocks, now)[0]
    run = run.take_decision(DilemmaId("captain"), OptionId("keep"), now)[0]
    return run.advance_block(BlockResolution(BlockId("opening"), state, b"\x00opaque\xff", cursor=date(2000, 2, 1)), now)[0]


def test_run_codec_round_trips_full_state_registry_decisions_cursor_and_opaque_payload() -> None:
    run = make_run()
    encoded = RunCodec.encode(run)
    decoded = RunCodec.decode(encoded)
    assert decoded == run
    assert decoded.block_records[0].payload == b"\x00opaque\xff"
    assert decoded.cursor == date(2000, 2, 1)
    assert decoded.run_state.squad_registry.transfers[0].to_club_season_id == ClubSeasonId("rival-fc-2000-01")


@pytest.mark.parametrize("payload", [b"{}", b'{"format_version":99}', b'{"format_version":1,"run":{}}'])
def test_run_codec_rejects_unknown_or_incomplete_formats(payload: bytes) -> None:
    with pytest.raises(InvalidValueError):
        RunCodec.decode(payload)


def test_run_codec_rejects_noncanonical_json() -> None:
    with pytest.raises(InvalidValueError):
        RunCodec.decode(b'{ "format_version": 1 }')
