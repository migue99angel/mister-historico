from datetime import UTC, datetime
from uuid import UUID

import pytest

from mister.game.domain.run import (
    BlockDefinition,
    BlockResolution,
    DecisionOption,
    DilemmaDefinition,
    Run,
    RunStatus,
)
from mister.game.domain.state import (
    CompetitionPriority,
    PlayerState,
    Position,
    Priority,
    RunState,
    Tactic,
    TacticStyle,
)
from mister.game.domain.squad_registry import Membership, SquadRegistry
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
        competition_priorities=(CompetitionPriority(CompetitionId("test-league"), Priority.NORMAL),),
        team_morale=50,
        board_confidence=50,
        state_as_of=None,
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
        run.advance_block(BlockResolution(make_state()), NOW)
    assert run.current_block == BLOCK_1


def test_advance_to_last_block_finishes_and_emits_block_and_finished_events() -> None:
    run, _ = make_run().take_decision(DILEMMA, OPTION, NOW)
    finished, events = run.advance_block(BlockResolution(make_state()), NOW)

    assert finished.status is RunStatus.FINISHED
    assert finished.current_block is None
    assert [type(event).__name__ for event in events] == ["BlockSimulated", "RunFinished"]


def test_sacked_run_emits_manager_sacked_and_rejects_further_commands() -> None:
    run = make_run()
    sacked, events = run.sack(NOW)

    assert sacked.status is RunStatus.SACKED
    assert type(events[0]).__name__ == "ManagerSacked"
    with pytest.raises(DomainError):
        sacked.take_decision(DILEMMA, OPTION, NOW)


def test_start_rejects_empty_or_repeated_blocks_without_creating_run() -> None:
    with pytest.raises(DomainError):
        Run.start(RunId(UUID(int=2)), PlayableSeasonId("test-fc-2000-01"), Seed(7), make_state(), (), NOW)
    with pytest.raises(DomainError):
        Run.start(
            RunId(UUID(int=2)),
            PlayableSeasonId("test-fc-2000-01"),
            Seed(7),
            make_state(),
            (BlockDefinition(BLOCK_1, ()), BlockDefinition(BLOCK_1, ())),
            NOW,
        )
