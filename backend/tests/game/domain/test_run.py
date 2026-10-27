from datetime import UTC, date, datetime
from uuid import UUID

import pytest

from mister.game.domain.run import (
    BlockDefinition,
    BlockRecord,
    BlockResolution,
    ClosureOutcome,
    DecisionOption,
    DilemmaDefinition,
    Run,
    RunStatus,
)
from mister.game.domain.squad_registry import Membership, SquadRegistry
from mister.game.domain.state import (
    CompetitionPriority,
    PlayerState,
    Position,
    Priority,
    RunState,
    Tactic,
    TacticStyle,
)
from mister.shared_kernel.errors import DomainError
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

NOW = datetime(2000, 1, 1, tzinfo=UTC)
PLAYER = PlayerId("keeper")
CLUB = ClubSeasonId("test-fc-2000-01")
BLOCK_1 = BlockId("opening")
BLOCK_2 = BlockId("closing")
DILEMMA = DilemmaId("captain")
OPTION = OptionId("keep-captain")


def make_state() -> RunState:
    return RunState(
        managed_club_season_id=CLUB,
        squad_registry=SquadRegistry((Membership(PLAYER, CLUB, None),)),
        players=(PlayerState(PLAYER, Position.GK, 80, 30, 50, 90),),
        tactic=Tactic(TacticStyle.BALANCED, (4, 3, 3)),
        competition_priorities=(
            CompetitionPriority(CompetitionId("test-league"), Priority.NORMAL),
        ),
        team_morale=50,
        board_confidence=50,
        state_as_of=None,
    )


def make_state_for(club: ClubSeasonId) -> RunState:
    state = make_state()
    return RunState(
        managed_club_season_id=club,
        squad_registry=SquadRegistry((Membership(PLAYER, club, None),)),
        players=state.players,
        tactic=state.tactic,
        competition_priorities=state.competition_priorities,
        team_morale=state.team_morale,
        board_confidence=state.board_confidence,
        state_as_of=state.state_as_of,
    )


def make_run() -> Run:
    opening = BlockDefinition(BLOCK_1, (DilemmaDefinition(DILEMMA, (DecisionOption(OPTION),)),))
    closing = BlockDefinition(BLOCK_2, ())
    return Run.start(
        RunId(UUID(int=1)),
        PlayableSeasonId("test-fc-2000-01"),
        Seed(7),
        make_state(),
        (opening, closing),
        NOW,
    )[0]


def test_start_creates_first_in_progress_block_and_emits_started() -> None:
    run, events = Run.start(
        RunId(UUID(int=1)),
        PlayableSeasonId("test-fc-2000-01"),
        Seed(7),
        make_state(),
        (BlockDefinition(BLOCK_1, ()),),
        NOW,
    )

    assert run.status is RunStatus.IN_PROGRESS
    assert run.current_block == BLOCK_1
    assert run.pending_dilemmas == ()
    assert len(events) == 1
    assert events[0].run_id == run.id


def test_take_decision_removes_pending_dilemma_and_emits_decision_taken() -> None:
    run = make_run()
    updated, events = run.take_decision(DILEMMA, OPTION, NOW)

    assert updated.decisions[0].option_id == OPTION
    assert updated.pending_dilemmas == ()
    assert events[0].dilemma_id == DILEMMA


def test_cannot_take_decision_twice_or_choose_option_from_another_dilemma() -> None:
    run = make_run()
    decided, _ = run.take_decision(DILEMMA, OPTION, NOW)

    with pytest.raises(DomainError):
        decided.take_decision(DILEMMA, OPTION, NOW)
    with pytest.raises(DomainError):
        run.take_decision(DILEMMA, OptionId("unknown-option"), NOW)

    assert run.decisions == ()


def test_advance_requires_all_dilemmas_resolved_and_does_not_mutate_on_error() -> None:
    run = make_run()
    with pytest.raises(DomainError):
        run.advance_block(BlockResolution(BLOCK_1, make_state()), NOW)
    assert run.current_block == BLOCK_1


def test_advance_progresses_to_next_block_then_finishes_after_last() -> None:
    run, _ = make_run().take_decision(DILEMMA, OPTION, NOW)
    second_block, first_events = run.advance_block(BlockResolution(BLOCK_1, make_state()), NOW)

    assert second_block.status is RunStatus.IN_PROGRESS
    assert second_block.current_block == BLOCK_2
    assert [type(event).__name__ for event in first_events] == ["BlockSimulated"]

    finished, events = second_block.advance_block(BlockResolution(BLOCK_2, make_state()), NOW)

    assert finished.status is RunStatus.FINISHED
    assert finished.current_block is None
    assert [type(event).__name__ for event in events] == ["BlockSimulated", "RunFinished"]


def test_sacked_run_emits_manager_sacked_and_rejects_further_commands() -> None:
    run = make_run()
    run, _ = run.take_decision(DILEMMA, OPTION, NOW)
    sacked, events = run.advance_block(
        BlockResolution(BLOCK_1, make_state(), ClosureOutcome.SACKED), NOW
    )

    assert sacked.status is RunStatus.SACKED
    assert [type(event).__name__ for event in events] == ["BlockSimulated", "ManagerSacked"]
    with pytest.raises(DomainError):
        sacked.take_decision(DILEMMA, OPTION, NOW)
    with pytest.raises(DomainError):
        sacked.advance_block(BlockResolution(BLOCK_1, make_state()), NOW)


def test_finished_run_rejects_commands() -> None:
    run = make_run()
    run, _ = run.take_decision(DILEMMA, OPTION, NOW)
    after_first, _ = run.advance_block(BlockResolution(BLOCK_1, make_state()), NOW)
    finished, _ = after_first.advance_block(BlockResolution(BLOCK_2, make_state()), NOW)

    with pytest.raises(DomainError):
        finished.take_decision(DILEMMA, OPTION, NOW)
    with pytest.raises(DomainError):
        finished.advance_block(BlockResolution(BLOCK_2, make_state()), NOW)


def test_start_rejects_empty_or_repeated_blocks_without_creating_run() -> None:
    with pytest.raises(DomainError):
        Run.start(
            RunId(UUID(int=2)), PlayableSeasonId("test-fc-2000-01"), Seed(7), make_state(), (), NOW
        )
    with pytest.raises(DomainError):
        Run.start(
            RunId(UUID(int=2)),
            PlayableSeasonId("test-fc-2000-01"),
            Seed(7),
            make_state(),
            (BlockDefinition(BLOCK_1, ()), BlockDefinition(BLOCK_1, ())),
            NOW,
        )


def test_take_decision_rejects_state_from_another_managed_club() -> None:
    run = make_run()

    with pytest.raises(DomainError):
        run.take_decision(DILEMMA, OPTION, NOW, make_state_for(ClubSeasonId("other-fc-2000-01")))

    assert run.decisions == ()


def test_advance_rejects_foreign_block_resolution_without_changing_run() -> None:
    run, _ = make_run().take_decision(DILEMMA, OPTION, NOW)

    with pytest.raises(DomainError):
        run.advance_block(BlockResolution(BLOCK_2, make_state()), NOW)

    assert run.current_block == BLOCK_1


def test_advance_rejects_state_from_another_managed_club() -> None:
    run, _ = make_run().take_decision(DILEMMA, OPTION, NOW)

    with pytest.raises(DomainError):
        run.advance_block(
            BlockResolution(BLOCK_1, make_state_for(ClubSeasonId("other-fc-2000-01"))), NOW
        )

    assert run.current_block == BLOCK_1


def test_advance_rejects_cursor_regression() -> None:
    run, _ = make_run().take_decision(DILEMMA, OPTION, NOW)
    with_cursor = Run(
        run.id,
        run.season_id,
        run.seed,
        run.status,
        run.run_state,
        run.blocks,
        run.block_index,
        run.decisions,
        cursor=date(2000, 2, 1),
    )

    with pytest.raises(DomainError):
        with_cursor.advance_block(
            BlockResolution(BLOCK_1, make_state(), cursor=date(2000, 1, 1)), NOW
        )

    assert with_cursor.cursor == date(2000, 2, 1)


def test_advance_retains_complete_opaque_block_payload() -> None:
    run, _ = make_run().take_decision(DILEMMA, OPTION, NOW)
    payload = b'{"away_goals":1,"extra_time":null,"penalties":null,"home_goals":1}'
    record = BlockRecord(BLOCK_1, payload)

    updated, _ = run.advance_block(BlockResolution(BLOCK_1, make_state(), payload=payload), NOW)

    assert updated.block_records == (record,)
    assert updated.block_records[0].payload == payload
