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
  `playable_season_id`, `created_at` and the full `replay_inputs` never change after `add`.
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
from datetime import date, datetime
from enum import StrEnum
from types import TracebackType
from typing import Protocol, Self

from mister.game.application.key_starter import (
    KeyStarterOffer as KeyStarterOffer,  # noqa: PLC0414 - published contract re-export
)
from mister.game.application.key_starter import (
    KeyStarterOutcome as KeyStarterOutcome,  # noqa: PLC0414 - published contract re-export
)
from mister.game.application.key_starter import (
    KeyStarterSelection as KeyStarterSelection,  # noqa: PLC0414 - published contract re-export
)
from mister.game.application.key_starter import (
    StarterAbsenceReason as StarterAbsenceReason,  # noqa: PLC0414 - published contract re-export
)
from mister.game.application.replay_inputs import ReplayInputs
from mister.game.application.run_content import RunContentSnapshot
from mister.shared_kernel.errors import DomainError, InvalidValueError
from mister.shared_kernel.ids import (
    BlockId,
    ClubSeasonId,
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
_MIN_UNRESOLVED_TIE_SIZE = 2
_KNOCKOUT_CLUB_COUNT = 2
_MAX_TIE_FIXTURES = 2

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
    """Persisted run state plus mandatory immutable inputs required for replay."""

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
    replay_inputs: ReplayInputs

    def __post_init__(self) -> None:
        if self.version < 0:
            raise InvalidValueError(f"version starts at 0, got {self.version}")
        if not self.run_token_hash.strip():
            raise InvalidValueError("run_token_hash must not be blank")
        if not isinstance(self.replay_inputs, ReplayInputs):
            raise InvalidValueError("run record needs complete replay inputs")
        if self.replay_inputs.content.playable_season_id != self.playable_season_id:
            raise InvalidValueError("replay content identity must match playable_season_id")
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
        `expected_version + 1` or if `seed`, `run_token_hash`, `playable_season_id`,
        `created_at` or `replay_inputs` differ from the stored ones ("immutable"), and
        `DecisionLogRewrittenError` if the stored decisions are not a prefix of `record.decisions`.
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


class Position(StrEnum):
    GK = "GK"
    DF = "DF"
    MF = "MF"
    FW = "FW"


class TeamVenue(StrEnum):
    """Where a match is played, from the managed team's point of view."""

    HOME = "home"
    AWAY = "away"
    NEUTRAL = "neutral"


class UserResult(StrEnum):
    """Outcome for the managed team, counting extra time and penalties."""

    WIN = "win"
    DRAW = "draw"
    LOSS = "loss"


class Side(StrEnum):
    HOME = "home"
    AWAY = "away"


class EventKind(StrEnum):
    """A notable fact of the block. New kinds are additive."""

    ADVANCED = "advanced"
    ELIMINATED = "eliminated"
    CHAMPION = "champion"


@dataclass(frozen=True, slots=True)
class TacticSetup:
    style: TacticStyle
    system: TacticSystem


@dataclass(frozen=True, slots=True)
class SquadPlayerState:
    """A player with his state: rating 1-99, morale and fitness 0-100.

    `injured_until` is the first day he is available again (`None` if healthy);
    `youth_minutes` marks a player the manager must give minutes to (dilemma effect).
    """

    player_id: PlayerId
    position: Position
    rating: int
    age: int | None
    morale: int
    fitness: int
    injured_until: date | None = None
    youth_minutes: bool = False


@dataclass(frozen=True, slots=True)
class TeamSquad:
    """A team as a squad plus a tactic: the managed team or a rival changed by transfers."""

    club_season_id: ClubSeasonId
    players: tuple[SquadPlayerState, ...]
    tactic: TacticSetup


@dataclass(frozen=True, slots=True)
class SquadMembership:
    """Inclusive player ownership interval for one simulated run."""

    player_id: PlayerId
    club_season_id: ClubSeasonId
    joined_on: date | None = None
    left_on: date | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.player_id, PlayerId) or not isinstance(
            self.club_season_id, ClubSeasonId
        ):
            raise InvalidValueError("squad membership needs typed player and club-season IDs")
        if any(
            value is not None and type(value) is not date
            for value in (self.joined_on, self.left_on)
        ):
            raise InvalidValueError("membership bounds must be dates or None")
        if (
            self.joined_on is not None
            and self.left_on is not None
            and self.joined_on > self.left_on
        ):
            raise InvalidValueError("membership joined_on must not be after left_on")


@dataclass(frozen=True, slots=True)
class ForcedInjury:
    """An injury applied on `date` for `days` days (from a dilemma effect)."""

    player_id: PlayerId
    date: date
    days: int


@dataclass(frozen=True, slots=True)
class ScoreLine:
    """Goals of the home and the away side."""

    home: int
    away: int


@dataclass(frozen=True, slots=True)
class MatchOutcome:
    """The result of a played fixture of the managed team.

    `regulation` is the 90 minutes, `extra_time` only the goals of those 30 minutes and
    `penalties` the shootout. `venue`, `opponent` and `user_result` are from the managed team's
    point of view; `winner` is the winning side (`None` for a drawn league match).
    """

    fixture_id: FixtureId
    competition_id: CompetitionId
    date: date
    home: ClubSeasonId
    away: ClubSeasonId
    regulation: ScoreLine
    venue: TeamVenue
    opponent: ClubSeasonId
    user_result: UserResult
    extra_time: ScoreLine | None = None
    penalties: ScoreLine | None = None
    winner: Side | None = None
    key: bool = False
    round: int | None = None
    stage_id: str | None = None
    group_id: str | None = None
    leg: int | None = None


@dataclass(frozen=True, slots=True)
class InjuryOutcome:
    """An injury suffered in the block (`forced` when it came from content or an effect)."""

    player_id: PlayerId
    date: date
    days: int
    forced: bool = False


@dataclass(frozen=True, slots=True)
class PlayerOutcome:
    """State of a managed player at the close of the block."""

    player_id: PlayerId
    fitness: int
    injured_until: date | None = None
    minutes_played: int = 0


@dataclass(frozen=True, slots=True)
class BlockEvent:
    """The managed team advances, is eliminated or wins a competition."""

    kind: EventKind
    date: date
    club_season_id: ClubSeasonId
    competition_id: CompetitionId
    stage_id: str | None = None


@dataclass(frozen=True, slots=True)
class StandingRow:
    club_season_id: ClubSeasonId
    position: int
    played: int
    won: int
    drawn: int
    lost: int
    goals_for: int
    goals_against: int
    points: int


@dataclass(frozen=True, slots=True)
class Standings:
    """A league table, or a group's table (`stage_id` and `group_id`), as of a date."""

    competition_id: CompetitionId
    as_of: date
    rows: tuple[StandingRow, ...]
    stage_id: str | None = None
    group_id: str | None = None
    unresolved_ties: tuple[tuple[ClubSeasonId, ...], ...] | None = None

    def __post_init__(self) -> None:
        if self.unresolved_ties is None:
            return
        if not isinstance(self.unresolved_ties, tuple):
            raise InvalidValueError("unresolved ties must be an immutable tuple or None")
        order = [row.club_season_id for row in self.rows]
        if len(set(order)) != len(order):
            raise InvalidValueError("unresolved standings need distinct row participants")
        occupied: set[ClubSeasonId] = set()
        for group in self.unresolved_ties:
            if (
                not isinstance(group, tuple)
                or len(group) < _MIN_UNRESOLVED_TIE_SIZE
                or not all(isinstance(club, ClubSeasonId) for club in group)
                or len(set(group)) != len(group)
                or not set(group) <= set(order)
            ):
                raise InvalidValueError("unresolved tie groups must contain row participants")
            if occupied.intersection(group):
                raise InvalidValueError("unresolved tie groups must be disjoint")
            indices = sorted(order.index(club) for club in group)
            if indices != list(range(indices[0], indices[-1] + 1)):
                raise InvalidValueError("unresolved tie groups must occupy contiguous rows")
            occupied.update(group)


@dataclass(frozen=True, slots=True)
class UnresolvedKnockoutTie:
    competition_id: CompetitionId
    stage_id: str
    clubs: tuple[ClubSeasonId, ...]
    fixture_ids: tuple[FixtureId, ...]

    def __post_init__(self) -> None:
        if (
            not isinstance(self.competition_id, CompetitionId)
            or not isinstance(self.stage_id, str)
            or not self.stage_id.strip()
            or not isinstance(self.clubs, tuple)
            or len(self.clubs) != _KNOCKOUT_CLUB_COUNT
            or not all(isinstance(club, ClubSeasonId) for club in self.clubs)
            or len(set(self.clubs)) != _KNOCKOUT_CLUB_COUNT
        ):
            raise InvalidValueError("an unresolved knockout tie needs a stage and two clubs")
        if (
            not isinstance(self.fixture_ids, tuple)
            or not 1 <= len(self.fixture_ids) <= _MAX_TIE_FIXTURES
            or not all(isinstance(fixture, FixtureId) for fixture in self.fixture_ids)
            or len(set(self.fixture_ids)) != len(self.fixture_ids)
        ):
            raise InvalidValueError("an unresolved tie needs one or two distinct fixture IDs")


@dataclass(frozen=True, slots=True)
class BlockSimulationRequest:
    """What Game asks of the engine for one block: the **run state**, nothing else.

    Game puts: the season (`playable_season_id`) and the run `seed`, the block (id and dates),
    the managed team with its tactic and team morale, the rivals changed by transfers
    (`team_overrides`, the effective squads from the `SquadRegistry`), the competition
    priorities, the injuries caused by dilemma effects and the results of earlier blocks.

    The adapter of T3.5 completes the reference content from `SeasonContentProvider`
    (participants, reference squads, competitions and stages, fixtures with their real result,
    historical standings, content-forced injuries, goal parameters) to build the engine's
    `SeasonSimInput`, and derives the engine's `RandomSource` from `seed`.
    """

    playable_season_id: PlayableSeasonId
    captured_content: RunContentSnapshot
    seed: Seed
    block_id: BlockId
    start: date
    end: date
    managed_team: TeamSquad
    team_morale: int
    team_overrides: tuple[TeamSquad, ...]
    competition_priorities: Mapping[CompetitionId, Priority]
    forced_injuries_from_effects: tuple[ForcedInjury, ...]
    prior_results: tuple[MatchOutcome, ...]
    state_as_of: date | None = None
    squad_memberships: tuple[SquadMembership, ...] | None = None
    player_pool: tuple[SquadPlayerState, ...] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.captured_content, RunContentSnapshot):
            raise InvalidValueError("simulation request needs captured content")
        if self.captured_content.playable_season_id != self.playable_season_id:
            raise InvalidValueError("captured content identity must match playable_season_id")
        if self.state_as_of is not None and not isinstance(self.state_as_of, date):
            raise InvalidValueError("state_as_of must be a date or None")
        _validate_dated_player_data(self.squad_memberships, self.player_pool)


def _validate_dated_player_data(
    memberships: tuple[SquadMembership, ...] | None,
    players: tuple[SquadPlayerState, ...] | None,
) -> None:
    if (memberships is None) != (players is None):
        raise InvalidValueError("dated memberships and player pool must be supplied together")
    if memberships is None or players is None:
        return
    if not isinstance(memberships, tuple) or not isinstance(players, tuple):
        raise InvalidValueError("dated squad collections must be immutable tuples")
    if any(not isinstance(item, SquadMembership) for item in memberships):
        raise InvalidValueError("squad_memberships must contain SquadMembership values")
    if any(not isinstance(item, SquadPlayerState) for item in players):
        raise InvalidValueError("player_pool must contain player states")
    pool_ids = tuple(player.player_id for player in players)
    if len(pool_ids) != len(set(pool_ids)):
        raise InvalidValueError("player_pool player IDs must be unique")
    if not {item.player_id for item in memberships} <= set(pool_ids):
        raise InvalidValueError("squad membership refers to a player outside player_pool")
    for index, item in enumerate(memberships):
        for other in memberships[index + 1 :]:
            if item.player_id != other.player_id:
                continue
            start_a = item.joined_on or date.min
            end_a = item.left_on or date.max
            start_b = other.joined_on or date.min
            end_b = other.left_on or date.max
            if start_a <= end_b and start_b <= end_a:
                raise InvalidValueError("a player cannot have overlapping memberships")


@dataclass(frozen=True, slots=True)
class BlockSimulationResult:
    """What the engine answers for a block (the engine's `BlockSummaryDTO`, in Game terms).

    Enough to rebuild the run state and the OpenAPI `BlockSummary` and `MatchReport`. Game
    derives, not the engine: the key-match label (`keyMatchLabel`), `previousPosition` (from
    the standings of the previous block), the competition and round display names, and the
    league position (read from `standings`).
    """

    block_id: BlockId
    matches: tuple[MatchOutcome, ...]
    key_matches: tuple[FixtureId, ...]
    standings: tuple[Standings, ...]
    events: tuple[BlockEvent, ...]
    injuries: tuple[InjuryOutcome, ...]
    player_states: tuple[PlayerOutcome, ...]
    unresolved_knockout_ties: tuple[UnresolvedKnockoutTie, ...] | None = None

    def __post_init__(self) -> None:
        if self.unresolved_knockout_ties is None:
            return
        if not isinstance(self.unresolved_knockout_ties, tuple):
            raise InvalidValueError("unresolved knockout ties must be an immutable tuple or None")
        used_fixtures: set[FixtureId] = set()
        occupied: set[tuple[CompetitionId, str, ClubSeasonId]] = set()
        for tie in self.unresolved_knockout_ties:
            if not isinstance(tie, UnresolvedKnockoutTie):
                raise InvalidValueError("unresolved knockout entries must be typed values")
            keys = {(tie.competition_id, tie.stage_id, club) for club in tie.clubs}
            if used_fixtures.intersection(tie.fixture_ids) or occupied.intersection(keys):
                raise InvalidValueError(
                    "unresolved ties cannot repeat fixtures or stage participants"
                )
            used_fixtures.update(tie.fixture_ids)
            occupied.update(keys)
            for match in self.matches:
                if match.fixture_id in tie.fixture_ids and (
                    match.competition_id != tie.competition_id
                    or match.stage_id != tie.stage_id
                    or {match.home, match.away} != set(tie.clubs)
                ):
                    raise InvalidValueError("a played result contradicts unresolved tie identity")


class SeasonSimulator(Protocol):
    """Game's port towards the engine (PLAN §3.1).

    The adapter of T3.5 translates to `simulation.application.api` (`BlockSimRequest` and
    `BlockSummaryDTO`; field mapping in `tests/game/test_simulator_dtos_mapping.py`).
    Deterministic: the same request always gives the same result.
    """

    def simulate_block(self, request: BlockSimulationRequest) -> BlockSimulationResult: ...
