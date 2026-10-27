from dataclasses import replace
from datetime import UTC, date, datetime
from uuid import UUID

import pytest

from mister.game.domain.run import (
    BlockDefinition,
    BlockRecord,
    BlockResolution,
    ClosureOutcome,
    Decision,
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
from mister.shared_kernel.errors import DomainError, InvalidValueError
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


def make_resolution(
    block_id: BlockId,
    state: RunState | None = None,
    outcome: ClosureOutcome = ClosureOutcome.CONTINUE,
    cursor: date | None = None,
) -> BlockResolution:
    return BlockResolution(
        block_id, state or make_state(), b"synthetic-block-output", outcome, cursor
    )


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
        run.advance_block(make_resolution(BLOCK_1), NOW)
    assert run.current_block == BLOCK_1


def test_advance_progresses_to_next_block_then_finishes_after_last() -> None:
    run, _ = make_run().take_decision(DILEMMA, OPTION, NOW)
    second_block, first_events = run.advance_block(make_resolution(BLOCK_1), NOW)

    assert second_block.status is RunStatus.IN_PROGRESS
    assert second_block.current_block == BLOCK_2
    assert [type(event).__name__ for event in first_events] == ["BlockSimulated"]

    finished, events = second_block.advance_block(make_resolution(BLOCK_2), NOW)

    assert finished.status is RunStatus.FINISHED
    assert finished.current_block is None
    assert finished.pending_dilemmas == ()
    assert [type(event).__name__ for event in events] == ["BlockSimulated", "RunFinished"]


def test_sacked_run_emits_manager_sacked_and_rejects_further_commands() -> None:
    run = make_run()
    run, _ = run.take_decision(DILEMMA, OPTION, NOW)
    sacked, events = run.advance_block(make_resolution(BLOCK_1, outcome=ClosureOutcome.SACKED), NOW)

    assert sacked.status is RunStatus.SACKED
    assert [type(event).__name__ for event in events] == ["BlockSimulated", "ManagerSacked"]
    with pytest.raises(DomainError):
        sacked.take_decision(DILEMMA, OPTION, NOW)
    with pytest.raises(DomainError):
        sacked.advance_block(make_resolution(BLOCK_1), NOW)


def test_finished_run_rejects_commands() -> None:
    run = make_run()
    run, _ = run.take_decision(DILEMMA, OPTION, NOW)
    after_first, _ = run.advance_block(make_resolution(BLOCK_1), NOW)
    finished, _ = after_first.advance_block(make_resolution(BLOCK_2), NOW)

    with pytest.raises(DomainError):
        finished.take_decision(DILEMMA, OPTION, NOW)
    with pytest.raises(DomainError):
        finished.advance_block(make_resolution(BLOCK_2), NOW)


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


def test_dilemma_rejects_empty_options() -> None:
    with pytest.raises(InvalidValueError):
        DilemmaDefinition(DILEMMA, ())


def test_dilemma_rejects_repeated_option_ids() -> None:
    option = DecisionOption(OPTION)
    with pytest.raises(InvalidValueError):
        DilemmaDefinition(DILEMMA, (option, option))


def test_block_rejects_repeated_dilemma_ids() -> None:
    dilemma = DilemmaDefinition(DILEMMA, (DecisionOption(OPTION),))
    with pytest.raises(InvalidValueError):
        BlockDefinition(BLOCK_1, (dilemma, dilemma))


def test_start_rejects_naive_event_time() -> None:
    with pytest.raises(InvalidValueError):
        Run.start(
            RunId(UUID(int=3)),
            PlayableSeasonId("test-fc-2000-01"),
            Seed(7),
            make_state(),
            (BlockDefinition(BLOCK_1, ()),),
            datetime(2000, 1, 1),
        )


def test_take_decision_rejects_naive_event_time() -> None:
    run = make_run()
    with pytest.raises(InvalidValueError):
        run.take_decision(DILEMMA, OPTION, datetime(2000, 1, 1))

    assert run.decisions == ()


@pytest.mark.parametrize(
    "create",
    [
        lambda: DecisionOption("option"),
        lambda: DilemmaDefinition("dilemma", (DecisionOption(OPTION),)),
        lambda: DilemmaDefinition(DILEMMA, (object(),)),
        lambda: BlockDefinition("block", ()),
        lambda: BlockDefinition(BLOCK_1, (object(),)),
        lambda: BlockRecord("block", b"payload"),
        lambda: BlockRecord(BLOCK_1, "payload"),
        lambda: BlockResolution("block", make_state(), b"payload"),
        lambda: BlockResolution(BLOCK_1, object(), b"payload"),
        lambda: BlockResolution(BLOCK_1, make_state(), "payload"),
        lambda: BlockResolution(BLOCK_1, make_state(), b"payload", "continue"),
        lambda: BlockResolution(
            BLOCK_1, make_state(), b"payload", cursor=datetime(2000, 1, 1, tzinfo=UTC)
        ),
    ],
)
def test_private_block_types_reject_invalid_values(create: object) -> None:
    with pytest.raises(InvalidValueError):
        create()  # type: ignore[operator]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", object()),
        ("season_id", object()),
        ("seed", object()),
        ("status", "in_progress"),
        ("blocks", ()),
        ("block_index", True),
        ("decisions", []),
        ("block_records", []),
        ("cursor", datetime(2000, 1, 1, tzinfo=UTC)),
    ],
)
def test_run_snapshot_rejects_invalid_fields(field: str, value: object) -> None:
    with pytest.raises(InvalidValueError):
        replace(make_run(), **{field: value})


def test_run_rejects_dilemma_ids_reused_in_another_block() -> None:
    run = make_run()
    second_block = BlockDefinition(
        BLOCK_2,
        (DilemmaDefinition(DILEMMA, (DecisionOption(OptionId("another-option")),)),),
    )

    with pytest.raises(InvalidValueError):
        replace(run, blocks=(run.blocks[0], second_block))


def test_different_dilemmas_may_reuse_option_ids_and_accept_decisions() -> None:
    run = make_run()
    other_id = DilemmaId("other-dilemma")
    other = DilemmaDefinition(other_id, (DecisionOption(OPTION),))
    first = BlockDefinition(BLOCK_1, (run.blocks[0].dilemmas[0], other))
    run = replace(run, blocks=(first, run.blocks[1]))

    run, _ = run.take_decision(DILEMMA, OPTION, NOW)
    run, events = run.take_decision(other_id, OPTION, NOW)

    assert tuple(decision.option_id for decision in run.decisions) == (OPTION, OPTION)
    assert events[0].dilemma_id == other_id


@pytest.mark.parametrize(
    "decisions",
    [
        (Decision(BLOCK_1, DILEMMA, OPTION, 2),),
        (Decision(BLOCK_1, DILEMMA, OPTION, True),),
        (Decision(BLOCK_1, DILEMMA, OPTION, 1), Decision(BLOCK_1, DILEMMA, OPTION, 2)),
        (Decision(BLOCK_1, DILEMMA, OptionId("unknown-option"), 1),),
    ],
)
def test_run_rejects_invalid_decision_history(decisions: tuple[Decision, ...]) -> None:
    with pytest.raises(InvalidValueError):
        replace(make_run(), decisions=decisions)


def test_run_rejects_duplicate_block_records() -> None:
    record = BlockRecord(BLOCK_1, b"payload")

    with pytest.raises(InvalidValueError):
        replace(make_run(), block_records=(record, record))


def test_take_decision_rejects_dilemma_outside_current_block() -> None:
    run = make_run()

    with pytest.raises(DomainError):
        run.take_decision(DilemmaId("unknown-dilemma"), OPTION, NOW)

    assert run.decisions == ()


def test_advance_rejects_naive_event_time() -> None:
    run = make_run()
    run, _ = run.take_decision(DILEMMA, OPTION, NOW)

    with pytest.raises(InvalidValueError):
        run.advance_block(make_resolution(BLOCK_1), datetime(2000, 1, 1))

    assert run.current_block == BLOCK_1


def test_take_decision_rejects_state_from_another_managed_club() -> None:
    run = make_run()

    with pytest.raises(DomainError):
        run.take_decision(DILEMMA, OPTION, NOW, make_state_for(ClubSeasonId("other-fc-2000-01")))

    assert run.decisions == ()


def test_take_decision_rejects_non_run_state() -> None:
    run = make_run()

    with pytest.raises(InvalidValueError):
        run.take_decision(DILEMMA, OPTION, NOW, object())

    assert run.decisions == ()


def test_advance_rejects_foreign_block_resolution_without_changing_run() -> None:
    run, _ = make_run().take_decision(DILEMMA, OPTION, NOW)

    with pytest.raises(DomainError):
        run.advance_block(make_resolution(BLOCK_2), NOW)

    assert run.current_block == BLOCK_1


def test_advance_rejects_state_from_another_managed_club() -> None:
    run, _ = make_run().take_decision(DILEMMA, OPTION, NOW)

    with pytest.raises(DomainError):
        run.advance_block(
            make_resolution(BLOCK_1, make_state_for(ClubSeasonId("other-fc-2000-01"))), NOW
        )

    assert run.current_block == BLOCK_1


def test_advance_rejects_cursor_regression() -> None:
    run, _ = make_run().take_decision(DILEMMA, OPTION, NOW)
    with_cursor, _ = run.advance_block(make_resolution(BLOCK_1, cursor=date(2000, 2, 1)), NOW)

    with pytest.raises(DomainError):
        with_cursor.advance_block(make_resolution(BLOCK_2, cursor=date(2000, 1, 1)), NOW)

    assert with_cursor.cursor == date(2000, 2, 1)


def test_run_cannot_skip_an_unclosed_block() -> None:
    with pytest.raises(InvalidValueError):
        replace(make_run(), block_index=1)


def test_run_records_must_be_exact_prefix_of_closed_blocks() -> None:
    with pytest.raises(InvalidValueError):
        replace(make_run(), block_records=(BlockRecord(BLOCK_2, b"foreign"),))


def test_run_cannot_close_a_block_with_an_unanswered_dilemma() -> None:
    opened, _ = make_run().take_decision(DILEMMA, OPTION, NOW)
    first_closed, _ = opened.advance_block(make_resolution(BLOCK_1), NOW)

    with pytest.raises(InvalidValueError):
        replace(first_closed, decisions=())


def test_run_cannot_contain_decisions_for_future_blocks() -> None:
    run = make_run()
    future_id = DilemmaId("future-dilemma")
    future_option = OptionId("future-option")
    future = BlockDefinition(
        BLOCK_2, (DilemmaDefinition(future_id, (DecisionOption(future_option),)),)
    )

    with pytest.raises(InvalidValueError):
        replace(
            run,
            blocks=(run.blocks[0], future),
            decisions=(Decision(BLOCK_2, future_id, future_option, 1),),
        )


def test_run_cursor_requires_a_closed_block_record() -> None:
    with pytest.raises(InvalidValueError):
        replace(make_run(), cursor=date(2000, 1, 1))


@pytest.mark.parametrize(
    ("status", "block_index", "records"),
    [
        (RunStatus.FINISHED, 1, ()),
        (RunStatus.SACKED, 0, ()),
        (RunStatus.IN_PROGRESS, 0, (BlockRecord(BlockId("unknown-block"), b"foreign"),)),
    ],
)
def test_run_terminal_status_and_records_must_match_closure(
    status: RunStatus, block_index: int, records: tuple[BlockRecord, ...]
) -> None:
    with pytest.raises(InvalidValueError):
        replace(make_run(), status=status, block_index=block_index, block_records=records)


def test_advance_retains_complete_opaque_block_payload() -> None:
    run, _ = make_run().take_decision(DILEMMA, OPTION, NOW)
    payload = b'{"away_goals":1,"extra_time":null,"penalties":null,"home_goals":1}'
    record = BlockRecord(BLOCK_1, payload)

    updated, _ = run.advance_block(BlockResolution(BLOCK_1, make_state(), payload=payload), NOW)

    assert updated.block_records == (record,)
    assert updated.block_records[0].payload == payload
