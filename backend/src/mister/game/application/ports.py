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
- **Version.** It starts at 0, like `RunView.version` in the OpenAPI. `save(record,
  expected_version)` succeeds only if the stored version equals `expected_version`, and
  `record.version` must be `expected_version + 1`. The caller bumps the version; the repository
  only checks it, so the stored record equals the saved one. `seed`, `run_token_hash`,
  `playable_season_id` and `created_at` never change after `add`.
- **JSON.** `snapshot` and the idempotent `response` are normalised as JSON on construction
  (tuples become lists, keys become strings), so a record equals what a JSONB column returns.
- **Idempotency.** The reply to a command is stored per `(run_id, key)` together with a hash of
  the request body (to tell a replay from `422 idempotency_key_conflict`). Stored replies are
  immutable: `put_idempotent` never overwrites. Keys have 8 to 128 characters (OpenAPI).
- **Transactions.** `UnitOfWork` groups the repository calls of one command: the run and its
  idempotency reply commit or roll back together. Repositories exist only inside a transaction.
- **Internal errors.** Errors that are not in the OpenAPI catalogue derive from `InternalError`:
  they signal a bug or an infrastructure fault, and the API layer (T3.6) maps them to
  `500` without exposing their `code`.
"""

import json
import re
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

MIN_IDEMPOTENCY_KEY_LENGTH = 8
MAX_IDEMPOTENCY_KEY_LENGTH = 128
_SYSTEM_PATTERN = re.compile(r"[1-9](-[1-9]){2,4}")
_OUTFIELD_PLAYERS = 10

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


class InternalError(DomainError):
    """A bug or an infrastructure fault, not part of the API error catalogue.

    The API layer maps it to `500` and never exposes its `code`.
    """

    code = "internal_error"


class RunAlreadyExistsError(InternalError):
    """`add` received a run id that is already stored (ids are generated, so this is a bug)."""

    code = "run_already_exists"

    def __init__(self, run_id: RunId) -> None:
        super().__init__(f"run {run_id} already exists")
        self.run_id = run_id


class DecisionLogRewrittenError(InternalError):
    """A save tried to change or drop decisions already logged (the log is append-only)."""

    code = "decision_log_rewritten"

    def __init__(self, run_id: RunId) -> None:
        super().__init__(f"the decision log of run {run_id} is append-only")
        self.run_id = run_id


class IdempotencyKeyExistsError(InternalError):
    """A reply is already stored for this run and `Idempotency-Key`.

    Two concurrent requests with the same key can both miss `get_idempotent`; the loser may get
    this error or a `ConcurrencyError` from `save`. In either case the use case reads
    `get_idempotent` again and answers with the stored reply (see `RunRepository`).
    """

    code = "idempotency_key_exists"

    def __init__(self, run_id: RunId, key: str) -> None:
        super().__init__(f"run {run_id} already has a reply for idempotency key {key!r}")
        self.run_id = run_id
        self.key = key


class NoActiveTransactionError(InternalError):
    """A repository was used outside a `with uow:` block."""

    code = "no_active_transaction"

    def __init__(self) -> None:
        super().__init__("the repositories can only be used inside a transaction")


# ----------------------------------------------------------------------------- persistence DTOs


def _require_aware(name: str, value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise InvalidValueError(f"{name} must be a timezone-aware datetime")


def _as_json(name: str, value: Mapping[str, object]) -> Mapping[str, object]:
    """`value` as a JSON round trip returns it (tuples to lists, keys to strings)."""
    try:
        normalised: Mapping[str, object] = json.loads(json.dumps(value, allow_nan=False))
    except (TypeError, ValueError) as error:
        raise InvalidValueError(f"{name} must be JSON-serialisable: {error}") from error
    return normalised


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
        if self.version < 0:
            raise InvalidValueError(f"version starts at 0, got {self.version}")
        if not self.run_token_hash.strip():
            raise InvalidValueError("run_token_hash must not be blank")
        object.__setattr__(self, "snapshot", _as_json("snapshot", self.snapshot))
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
        if not MIN_IDEMPOTENCY_KEY_LENGTH <= len(self.key) <= MAX_IDEMPOTENCY_KEY_LENGTH:
            raise InvalidValueError(
                f"idempotency key must have {MIN_IDEMPOTENCY_KEY_LENGTH} to "
                f"{MAX_IDEMPOTENCY_KEY_LENGTH} characters"
            )
        if not self.request_hash:
            raise InvalidValueError("request_hash must not be empty")
        object.__setattr__(self, "response", _as_json("response", self.response))
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
        `expected_version + 1` or if `seed`, `run_token_hash`, `playable_season_id` or
        `created_at` differ from the stored ones ("immutable"), and `DecisionLogRewrittenError`
        if the stored decisions are not a prefix of `record.decisions`.
        """
        ...

    def get_idempotent(self, run_id: RunId, key: str) -> IdempotencyRecord | None:
        """The reply stored for this run and key, or `None`."""
        ...

    def put_idempotent(self, record: IdempotencyRecord) -> None:
        """Store a reply for an existing run, never overwriting one.

        Raises `RunNotFoundError` for an unknown run and `IdempotencyKeyExistsError` if the key
        already has a reply.

        Concurrent requests with the same key: both miss `get_idempotent` and both try to
        write. The loser gets `ConcurrencyError` (its `save` runs first) or
        `IdempotencyKeyExistsError`. The use case must then roll back, call `get_idempotent`
        again and return the stored original reply instead of failing.
        """
        ...


class UnitOfWork(Protocol):
    """A transaction over the Game repositories.

    Usable as a context manager, once per transaction. Leaving the block without `commit()`
    (or after an exception, which propagates) rolls everything back.
    """

    @property
    def runs(self) -> RunRepository:
        """The repository of the current transaction.

        Raises `NoActiveTransactionError` outside a `with` block.
        """
        ...

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


class TacticStyle(StrEnum):
    """Playing styles (canonical vocabulary of the content format and the API)."""

    PRESSING = "pressing"
    COUNTER = "counter"
    POSSESSION = "possession"
    BALANCED = "balanced"


class Priority(StrEnum):
    """How much the manager prioritises a competition."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


@dataclass(frozen=True, slots=True)
class TacticSystem:
    """A formation as outfield lines (`4-3-3`): 3 to 5 lines of 1 to 6 players, 10 in total."""

    value: str

    def __post_init__(self) -> None:
        if _SYSTEM_PATTERN.fullmatch(self.value) is None:
            raise InvalidValueError(f"system must look like 4-3-3, got {self.value!r}")
        lines = [int(line) for line in self.value.split("-")]
        if sum(lines) != _OUTFIELD_PLAYERS or max(lines) > 6:  # noqa: PLR2004
            raise InvalidValueError(f"system must add up to 10 outfield players: {self.value!r}")

    def __str__(self) -> str:
        return self.value


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
    tactic_style: TacticStyle
    tactic_system: TacticSystem
    competition_priorities: Mapping[CompetitionId, Priority]


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
