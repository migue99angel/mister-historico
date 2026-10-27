"""Immutable aggregate and state machine for one game run."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from mister.game.domain.errors import (
    AlreadyDecidedError,
    InvalidDecisionError,
    InvalidRunTransitionError,
)
from mister.game.domain.events import (
    BlockSimulated,
    DecisionTaken,
    ManagerSacked,
    RunFinished,
    RunStarted,
)
from mister.game.domain.state import RunState
from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import (
    BlockId,
    DilemmaId,
    OptionId,
    PlayableSeasonId,
    RunId,
)
from mister.shared_kernel.seed import Seed


class RunStatus(StrEnum):
    """Lifecycle status for a run."""

    IN_PROGRESS = "in_progress"
    FINISHED = "finished"
    SACKED = "sacked"


class ClosureOutcome(StrEnum):
    """Explicit decision supplied by the block resolver about the manager's job."""

    CONTINUE = "continue"
    SACKED = "sacked"


@dataclass(frozen=True, slots=True)
class DecisionOption:
    """A private option identity accepted for a dilemma."""

    id: OptionId

    def __post_init__(self) -> None:
        if not isinstance(self.id, OptionId):
            raise InvalidValueError("decision option requires an OptionId")


@dataclass(frozen=True, slots=True)
class DilemmaDefinition:
    """A private dilemma definition for a season block."""

    id: DilemmaId
    options: tuple[DecisionOption, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.id, DilemmaId):
            raise InvalidValueError("dilemma requires a DilemmaId")
        if (
            not isinstance(self.options, tuple)
            or not self.options
            or any(not isinstance(option, DecisionOption) for option in self.options)
        ):
            raise InvalidValueError("dilemma options must be a non-empty tuple")
        if len({option.id for option in self.options}) != len(self.options):
            raise InvalidValueError("dilemma option IDs must be unique")


@dataclass(frozen=True, slots=True)
class BlockDefinition:
    """A private block definition and the dilemmas offered during it."""

    id: BlockId
    dilemmas: tuple[DilemmaDefinition, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.id, BlockId):
            raise InvalidValueError("block requires a BlockId")
        if not isinstance(self.dilemmas, tuple) or any(
            not isinstance(dilemma, DilemmaDefinition) for dilemma in self.dilemmas
        ):
            raise InvalidValueError("block dilemmas must be an immutable tuple")
        if len({dilemma.id for dilemma in self.dilemmas}) != len(self.dilemmas):
            raise InvalidValueError("dilemma IDs must be unique within a block")


@dataclass(frozen=True, slots=True)
class Decision:
    """An immutable, sequenced decision made in a specific block."""

    block_id: BlockId
    dilemma_id: DilemmaId
    option_id: OptionId
    sequence: int


@dataclass(frozen=True, slots=True)
class BlockRecord:
    """Lossless opaque output for one block, serialized and decoded by T3.5 adapters."""

    block_id: BlockId
    payload: bytes

    def __post_init__(self) -> None:
        if not isinstance(self.block_id, BlockId):
            raise InvalidValueError("block record requires a BlockId")
        if not isinstance(self.payload, bytes):
            raise InvalidValueError("block record payload must be immutable bytes")


@dataclass(frozen=True, slots=True)
class BlockResolution:
    """Already-calculated complete block output and explicit closure resolution.

    The opaque payload preserves results, standings, unresolved ties and any other simulation
    fields losslessly. Adapters own its serialization contract; this domain never decodes it.
    """

    block_id: BlockId
    run_state: RunState
    payload: bytes
    outcome: ClosureOutcome = ClosureOutcome.CONTINUE
    cursor: date | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.block_id, BlockId) or not isinstance(self.run_state, RunState):
            raise InvalidValueError("block resolution requires a BlockId and RunState")
        if not isinstance(self.outcome, ClosureOutcome):
            raise InvalidValueError("outcome must be a ClosureOutcome")
        if not isinstance(self.payload, bytes):
            raise InvalidValueError("block resolution payload must be immutable bytes")
        if self.cursor is not None and (
            not isinstance(self.cursor, date) or isinstance(self.cursor, datetime)
        ):
            raise InvalidValueError("cursor must be a date or None")


@dataclass(frozen=True, slots=True)
class Run:
    """Immutable run state; commands return a replacement and its domain events."""

    id: RunId
    season_id: PlayableSeasonId
    seed: Seed
    status: RunStatus
    run_state: RunState
    blocks: tuple[BlockDefinition, ...]
    block_index: int
    decisions: tuple[Decision, ...] = ()
    block_records: tuple[BlockRecord, ...] = ()
    cursor: date | None = None

    def __post_init__(self) -> None:  # noqa: PLR0912, PLR0915 - validate aggregate invariants
        if not isinstance(self.id, RunId) or not isinstance(self.season_id, PlayableSeasonId):
            raise InvalidValueError("run requires a RunId and PlayableSeasonId")
        if not isinstance(self.seed, Seed) or not isinstance(self.run_state, RunState):
            raise InvalidValueError("run requires a Seed and RunState")
        if not isinstance(self.status, RunStatus):
            raise InvalidValueError("status must be a RunStatus")
        if (
            not isinstance(self.blocks, tuple)
            or not self.blocks
            or any(not isinstance(block, BlockDefinition) for block in self.blocks)
        ):
            raise InvalidValueError("run blocks must be a non-empty tuple")
        if len({block.id for block in self.blocks}) != len(self.blocks):
            raise InvalidValueError("block IDs must be unique")
        all_dilemmas = [dilemma.id for block in self.blocks for dilemma in block.dilemmas]
        if len(set(all_dilemmas)) != len(all_dilemmas):
            raise InvalidValueError("dilemma IDs must be unique in a run")
        if type(self.block_index) is not int or not 0 <= self.block_index < len(self.blocks):
            raise InvalidValueError("block_index must identify a run block")
        if not isinstance(self.decisions, tuple) or any(
            not isinstance(decision, Decision) for decision in self.decisions
        ):
            raise InvalidValueError("decisions must be an immutable tuple")
        if any(type(decision.sequence) is not int for decision in self.decisions):
            raise InvalidValueError("decision sequence values must be integers")
        if [decision.sequence for decision in self.decisions] != list(
            range(1, len(self.decisions) + 1)
        ):
            raise InvalidValueError("decision sequence must be contiguous")
        if len({decision.dilemma_id for decision in self.decisions}) != len(self.decisions):
            raise InvalidValueError("a dilemma can only be decided once")
        known_decisions = {
            (block.id, dilemma.id, option.id)
            for block in self.blocks
            for dilemma in block.dilemmas
            for option in dilemma.options
        }
        if any(
            (decision.block_id, decision.dilemma_id, decision.option_id) not in known_decisions
            for decision in self.decisions
        ):
            raise InvalidValueError("decisions must reference a defined dilemma option")
        block_indexes = {block.id: index for index, block in enumerate(self.blocks)}
        decision_block_indexes = [block_indexes[decision.block_id] for decision in self.decisions]
        if decision_block_indexes != sorted(decision_block_indexes):
            raise InvalidValueError("decisions must follow block order")
        if any(index > self.block_index for index in decision_block_indexes):
            raise InvalidValueError("decisions cannot belong to a future block")
        if not isinstance(self.block_records, tuple) or any(
            not isinstance(record, BlockRecord) for record in self.block_records
        ):
            raise InvalidValueError("block_records must be an immutable tuple")
        if len({record.block_id for record in self.block_records}) != len(self.block_records):
            raise InvalidValueError("a block closure record can only be stored once")
        closed_count = len(self.block_records)
        if self.status is RunStatus.IN_PROGRESS and closed_count != self.block_index:
            raise InvalidValueError("in-progress runs need a record for every prior block")
        if self.status is RunStatus.FINISHED and (
            self.block_index != len(self.blocks) - 1 or closed_count != len(self.blocks)
        ):
            raise InvalidValueError("finished runs must close every block")
        if self.status is RunStatus.SACKED and closed_count != self.block_index + 1:
            raise InvalidValueError("sacked runs must close the dismissal block")
        if any(
            record.block_id != self.blocks[index].id
            for index, record in enumerate(self.block_records)
        ):
            raise InvalidValueError("block records must be the exact prefix of closed blocks")
        closed_dilemmas = {
            dilemma.id for block in self.blocks[:closed_count] for dilemma in block.dilemmas
        }
        decided_dilemmas = {decision.dilemma_id for decision in self.decisions}
        if not closed_dilemmas <= decided_dilemmas:
            raise InvalidValueError("every closed block dilemma must have a decision")
        if self.cursor is not None and closed_count == 0:
            raise InvalidValueError("run cursor requires a closed block record")
        if self.cursor is not None and (
            not isinstance(self.cursor, date) or isinstance(self.cursor, datetime)
        ):
            raise InvalidValueError("cursor must be a date or None")

    @property
    def current_block(self) -> BlockId | None:
        """Current block ID, or None once the run is terminal."""
        return self.blocks[self.block_index].id if self.status is RunStatus.IN_PROGRESS else None

    @property
    def pending_dilemmas(self) -> tuple[DilemmaId, ...]:
        """Dilemmas in the current block that have not yet been decided."""
        if self.status is not RunStatus.IN_PROGRESS:
            return ()
        decided = {decision.dilemma_id for decision in self.decisions}
        return tuple(
            dilemma.id
            for dilemma in self.blocks[self.block_index].dilemmas
            if dilemma.id not in decided
        )

    @classmethod
    def start(  # noqa: PLR0913, PLR0917 - explicit aggregate inputs
        cls,
        run_id: RunId,
        season_id: PlayableSeasonId,
        seed: Seed,
        run_state: RunState,
        blocks: tuple[BlockDefinition, ...],
        occurred_at: datetime,
    ) -> tuple[Run, tuple[RunStarted, ...]]:
        """Create an in-progress run and emit its start event."""
        if occurred_at.tzinfo is None or occurred_at.utcoffset() is None:
            raise InvalidValueError("occurred_at must be timezone-aware")
        run = cls(run_id, season_id, seed, RunStatus.IN_PROGRESS, run_state, blocks, 0)
        return run, (
            RunStarted(occurred_at=occurred_at, run_id=run_id, season_id=season_id, seed=seed),
        )

    def take_decision(
        self,
        dilemma_id: DilemmaId,
        option_id: OptionId,
        occurred_at: datetime,
        resulting_state: RunState | None = None,
    ) -> tuple[Run, tuple[DecisionTaken, ...]]:
        """Record a choice and optionally its already-calculated state effects."""
        self._require_in_progress()
        block = self.blocks[self.block_index]
        dilemma = next((item for item in block.dilemmas if item.id == dilemma_id), None)
        if dilemma is None:
            raise InvalidDecisionError("dilemma does not belong to the current block")
        if any(decision.dilemma_id == dilemma_id for decision in self.decisions):
            raise AlreadyDecidedError("dilemma has already been decided")
        if option_id not in {option.id for option in dilemma.options}:
            raise InvalidDecisionError("option does not belong to the selected dilemma")
        state = resulting_state or self.run_state
        self._validate_club(state)
        self._validate_time(occurred_at)
        decision = Decision(block.id, dilemma_id, option_id, len(self.decisions) + 1)
        new_run = self.__class__(
            self.id,
            self.season_id,
            self.seed,
            self.status,
            state,
            self.blocks,
            self.block_index,
            (*self.decisions, decision),
            self.block_records,
            self.cursor,
        )
        event = DecisionTaken(
            occurred_at=occurred_at,
            run_id=self.id,
            block_id=block.id,
            dilemma_id=dilemma_id,
            option_id=option_id,
            sequence=decision.sequence,
        )
        return new_run, (event,)

    def advance_block(
        self, resolution: BlockResolution, occurred_at: datetime
    ) -> tuple[Run, tuple[BlockSimulated | ManagerSacked | RunFinished, ...]]:
        """Apply a precomputed block output and advance, finish, or sack the manager."""
        self._require_in_progress()
        self._validate_time(occurred_at)
        if self.pending_dilemmas:
            raise InvalidRunTransitionError("all current block dilemmas must be decided first")
        block = self.blocks[self.block_index]
        if resolution.block_id != block.id:
            raise InvalidRunTransitionError("resolution does not belong to the current block")
        self._validate_club(resolution.run_state)
        if (
            self.cursor is not None
            and resolution.cursor is not None
            and resolution.cursor < self.cursor
        ):
            raise InvalidRunTransitionError("run cursor cannot move backwards")
        base = BlockSimulated(
            occurred_at=occurred_at,
            run_id=self.id,
            block_id=block.id,
            block_number=self.block_index + 1,
        )
        record = BlockRecord(block.id, resolution.payload)
        next_records = (*self.block_records, record)
        next_cursor = resolution.cursor if resolution.cursor is not None else self.cursor
        if resolution.outcome is ClosureOutcome.SACKED:
            updated = self._replace(
                status=RunStatus.SACKED,
                run_state=resolution.run_state,
                block_records=next_records,
                cursor=next_cursor,
            )
            return updated, (
                base,
                ManagerSacked(occurred_at=occurred_at, run_id=self.id, block_id=block.id),
            )
        if self.block_index + 1 == len(self.blocks):
            updated = self._replace(
                status=RunStatus.FINISHED,
                run_state=resolution.run_state,
                block_records=next_records,
                cursor=next_cursor,
            )
            return updated, (base, RunFinished(occurred_at=occurred_at, run_id=self.id))
        updated = self._replace(
            run_state=resolution.run_state,
            block_index=self.block_index + 1,
            block_records=next_records,
            cursor=next_cursor,
        )
        return updated, (base,)

    def _replace(self, **changes: object) -> Run:
        values: dict[str, object] = {
            "id": self.id,
            "season_id": self.season_id,
            "seed": self.seed,
            "status": self.status,
            "run_state": self.run_state,
            "blocks": self.blocks,
            "block_index": self.block_index,
            "decisions": self.decisions,
            "block_records": self.block_records,
            "cursor": self.cursor,
        }
        values.update(changes)
        return Run(**values)  # type: ignore[arg-type]

    def _require_in_progress(self) -> None:
        if self.status is not RunStatus.IN_PROGRESS:
            raise InvalidRunTransitionError("terminal runs reject commands")

    def _validate_club(self, state: RunState) -> None:
        if not isinstance(state, RunState):
            raise InvalidValueError("state must be a RunState")
        if state.managed_club_season_id != self.run_state.managed_club_season_id:
            raise InvalidRunTransitionError("run state belongs to another managed club")

    @staticmethod
    def _validate_time(value: datetime) -> None:
        if value.tzinfo is None or value.utcoffset() is None:
            raise InvalidValueError("occurred_at must be timezone-aware")
