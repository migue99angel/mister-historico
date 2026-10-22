"""Application ports of the Game context, with the DTOs they exchange.

Persistence (ADR-009 of PLAN §3.3): a run is stored as a JSON **snapshot** of its state plus an
append-only **log of decisions**, guarded by optimistic locking on `version`. The `Run`
aggregate does not exist yet (T3.1), so the repository speaks in `RunRecord`, a persistence
DTO that carries the aggregate as a JSON-serialisable mapping. Replay (T3.5) rebuilds a run
from `seed` and `decisions` and compares it with `snapshot`.

Decisions recorded here:

- **Run token.** The client's bearer token is never stored. `RunRecord.run_token_hash` holds
  the output of `RunTokenHasher.hash`. The token is 32 random bytes, so a fast unsalted
  SHA-256 is enough (there is nothing to brute-force, unlike a human password); the port lets
  a real adapter pick another algorithm without touching the use cases. Generating the token is
  a separate port (`RunTokenGenerator`) so tests get deterministic tokens.
- **Version.** `save(record, expected_version)` succeeds only if the stored version equals
  `expected_version`, and `record.version` must be `expected_version + 1`. The caller bumps the
  version; the repository only checks it, so the stored record equals the saved one.
- **Idempotency.** The reply to a command is stored per `(run_id, key)` together with a hash of
  the request body (to tell a replay from `422 idempotency_key_conflict`). Stored replies are
  immutable: `put_idempotent` never overwrites.
- **Transactions.** `UnitOfWork` groups the repository calls of one command: the run and its
  idempotency reply commit or roll back together.
"""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from types import TracebackType
from typing import Protocol, Self

from mister.shared_kernel.errors import DomainError, InvalidValueError
from mister.shared_kernel.ids import (
    BlockId,
    CompetitionId,
    DilemmaId,
    FixtureId,
    OptionId,
    PlayableSeasonId,
    PlayerId,
    RunId,
)
from mister.shared_kernel.seed import Seed

MAX_IDEMPOTENCY_KEY_LENGTH = 255

# ----------------------------------------------------------------------------- errors


class ConcurrencyError(DomainError):
    """Another writer saved the run first (API: `409 version_conflict`)."""

    code = "version_conflict"

    def __init__(self, run_id: RunId, *, expected: int) -> None:
        super().__init__(f"run {run_id} is no longer at version {expected}")
        self.run_id = run_id
        self.expected = expected


class RunNotFoundError(DomainError):
    """The run does not exist (API: `404 run_not_found`)."""

    code = "run_not_found"

    def __init__(self, run_id: RunId) -> None:
        super().__init__(f"run {run_id} not found")
        self.run_id = run_id


class RunAlreadyExistsError(DomainError):
    """`add` received a run id that is already stored."""

    code = "run_already_exists"

    def __init__(self, run_id: RunId) -> None:
        super().__init__(f"run {run_id} already exists")
        self.run_id = run_id


class DecisionLogRewrittenError(DomainError):
    """A save tried to change or drop decisions already logged (the log is append-only)."""

    code = "decision_log_rewritten"

    def __init__(self, run_id: RunId) -> None:
        super().__init__(f"the decision log of run {run_id} is append-only")
        self.run_id = run_id


class IdempotencyKeyExistsError(DomainError):
    """A reply is already stored for this run and `Idempotency-Key`."""

    code = "idempotency_key_exists"

    def __init__(self, run_id: RunId, key: str) -> None:
        super().__init__(f"run {run_id} already has a reply for idempotency key {key!r}")
        self.run_id = run_id
        self.key = key


# ----------------------------------------------------------------------------- persistence DTOs


def _require_aware(name: str, value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise InvalidValueError(f"{name} must be a timezone-aware datetime")


def _require_json(name: str, value: Mapping[str, object]) -> None:
    try:
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise InvalidValueError(f"{name} must be JSON-serialisable: {error}") from error


class RunStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"
    SACKED = "sacked"


@dataclass(frozen=True, slots=True)
class DecisionRecord:
    """One entry of the decision log. `sequence` is one-based and has no gaps."""

    sequence: int
    block_id: BlockId
    dilemma_id: DilemmaId
    option_id: OptionId
    decided_at: datetime

    def __post_init__(self) -> None:
        _require_aware("decided_at", self.decided_at)


@dataclass(frozen=True, slots=True)
class RunRecord:
    """A run as persisted: JSON snapshot, decision log and the version for optimistic locking."""

    run_id: RunId
    playable_season_id: PlayableSeasonId
    seed: Seed
    run_token_hash: str
    version: int
    status: RunStatus
    snapshot: Mapping[str, object]
    decisions: tuple[DecisionRecord, ...]
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        if self.version < 1:
            raise InvalidValueError(f"version starts at 1, got {self.version}")
        if not self.run_token_hash.strip():
            raise InvalidValueError("run_token_hash must not be blank")
        _require_json("snapshot", self.snapshot)
        _require_aware("created_at", self.created_at)
        _require_aware("updated_at", self.updated_at)
        if self.updated_at < self.created_at:
            raise InvalidValueError("updated_at must not be before created_at")
        if [d.sequence for d in self.decisions] != list(range(1, len(self.decisions) + 1)):
            raise InvalidValueError("decision sequence must be 1..n without gaps")


@dataclass(frozen=True, slots=True)
class IdempotencyRecord:
    """The stored reply to a command, keyed by run and `Idempotency-Key`."""

    run_id: RunId
    key: str
    request_hash: str
    response: Mapping[str, object]
    created_at: datetime

    def __post_init__(self) -> None:
        if not 1 <= len(self.key) <= MAX_IDEMPOTENCY_KEY_LENGTH:
            raise InvalidValueError(
                f"idempotency key must have 1 to {MAX_IDEMPOTENCY_KEY_LENGTH} characters"
            )
        if not self.request_hash:
            raise InvalidValueError("request_hash must not be empty")
        _require_json("response", self.response)
        _require_aware("created_at", self.created_at)


# ----------------------------------------------------------------------------- repository, UoW


class RunRepository(Protocol):
    """Persistence of runs with optimistic locking (ADR-009)."""

    def add(self, record: RunRecord) -> None:
        """Store a new run; raises `RunAlreadyExistsError` if the id is taken."""
        ...

    def get(self, run_id: RunId) -> RunRecord | None:
        """The stored run, or `None`. The result never aliases the repository's state."""
        ...

    def save(self, record: RunRecord, expected_version: int) -> None:
        """Replace the stored run with `record`.

        Raises `RunNotFoundError` if unknown, `ConcurrencyError` if the stored version is not
        `expected_version`, `InvalidValueError` if `record.version` is not
        `expected_version + 1`, and `DecisionLogRewrittenError` if the stored decisions are not
        a prefix of `record.decisions`.
        """
        ...

    def get_idempotent(self, run_id: RunId, key: str) -> IdempotencyRecord | None:
        """The reply stored for this run and key, or `None`."""
        ...

    def put_idempotent(self, record: IdempotencyRecord) -> None:
        """Store a reply; raises `IdempotencyKeyExistsError` if the key already has one."""
        ...


class UnitOfWork(Protocol):
    """A transaction over the Game repositories.

    Usable as a context manager, once per transaction. Leaving the block without `commit()`
    (or after an exception, which propagates) rolls everything back.
    """

    @property
    def runs(self) -> RunRepository: ...

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


# ----------------------------------------------------------------------------- run token


class RunTokenGenerator(Protocol):
    """Creates the secret bearer token of a run."""

    def generate(self) -> str:
        """A new URL-safe token of at least 32 random bytes (43 characters)."""
        ...


class RunTokenHasher(Protocol):
    """Hashes run tokens so the raw token is never stored."""

    def hash(self, token: str) -> str: ...

    def verify(self, token: str, token_hash: str) -> bool:
        """Whether `token` hashes to `token_hash` (in constant time)."""
        ...


# ----------------------------------------------------------------------------- simulator


@dataclass(frozen=True, slots=True)
class SquadMemberState:
    """A player of the effective squad as the engine needs him (morale and fitness 0-100)."""

    player_id: PlayerId
    rating: int
    morale: int
    fitness: int
    available: bool


@dataclass(frozen=True, slots=True)
class BlockSimulationRequest:
    """What Game asks of the engine for one block.

    Deliberately simple: the adapter of T3.5 completes it with the season content it already
    reads through the Catalog ACL. Extending this DTO is a contract change.
    """

    playable_season_id: PlayableSeasonId
    seed: Seed
    block_id: BlockId
    squad: tuple[SquadMemberState, ...]
    tactic_style: str
    tactic_system: str
    competition_priorities: Mapping[CompetitionId, str]


@dataclass(frozen=True, slots=True)
class MatchOutcome:
    """The result of a match of the own team, from its point of view."""

    fixture_id: FixtureId
    competition_id: CompetitionId
    goals_for: int
    goals_against: int
    extra_time: bool = False
    penalties_for: int | None = None
    penalties_against: int | None = None


@dataclass(frozen=True, slots=True)
class InjuryOutcome:
    player_id: PlayerId
    days: int


@dataclass(frozen=True, slots=True)
class BlockSimulationResult:
    """What the engine answers for a block."""

    block_id: BlockId
    matches: tuple[MatchOutcome, ...]
    injuries: tuple[InjuryOutcome, ...]
    minutes_played: Mapping[PlayerId, int]
    league_positions: Mapping[CompetitionId, int]


class SeasonSimulator(Protocol):
    """Game's port towards the engine (PLAN §3.1).

    The adapter of T3.5 translates to `simulation.application.api`. Deterministic: the same
    request always gives the same result.
    """

    def simulate_block(self, request: BlockSimulationRequest) -> BlockSimulationResult: ...
