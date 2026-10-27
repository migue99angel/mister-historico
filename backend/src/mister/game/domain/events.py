"""Private lifecycle events emitted by a game run."""

from dataclasses import dataclass

from mister.shared_kernel.events import DomainEvent
from mister.shared_kernel.ids import BlockId, DilemmaId, OptionId, PlayableSeasonId, RunId
from mister.shared_kernel.seed import Seed


@dataclass(frozen=True, kw_only=True)
class RunStarted(DomainEvent):
    """A new run was created."""

    run_id: RunId
    season_id: PlayableSeasonId
    seed: Seed


@dataclass(frozen=True, kw_only=True)
class DecisionTaken(DomainEvent):
    """A manager selected an option in a dilemma."""

    run_id: RunId
    block_id: BlockId
    dilemma_id: DilemmaId
    option_id: OptionId
    sequence: int


@dataclass(frozen=True, kw_only=True)
class BlockSimulated(DomainEvent):
    """The current block was resolved by the simulation engine."""

    run_id: RunId
    block_id: BlockId
    block_number: int


@dataclass(frozen=True, kw_only=True)
class ManagerSacked(DomainEvent):
    """The board dismissed the manager after a block."""

    run_id: RunId
    block_id: BlockId


@dataclass(frozen=True, kw_only=True)
class RunFinished(DomainEvent):
    """The final block was completed."""

    run_id: RunId
