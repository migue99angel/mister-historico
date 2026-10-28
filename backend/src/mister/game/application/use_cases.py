"""Private application use cases for starting and recording decisions in a run."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import datetime
from typing import TYPE_CHECKING, cast

from mister.game.application import ports
from mister.game.application.replay_inputs import ReplayInputs
from mister.game.application.rules import RulesConfiguration
from mister.game.application.run_codec import decode_run, encode_run
from mister.game.domain import effects
from mister.game.domain.board import GoalProgress, GoalStatus
from mister.game.domain.run import Run
from mister.shared_kernel.errors import DomainError, InvalidValueError
from mister.shared_kernel.ids import DilemmaId, OptionId, PlayableSeasonId, RunId

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from mister.game.application.content_model import CapturedSeason
    from mister.game.application.run_content import RunContentSnapshot
    from mister.game.domain.state import RunState
    from mister.shared_kernel.clock import Clock
    from mister.shared_kernel.events import DomainEvent, EventBus
    from mister.shared_kernel.seed import Seed

_SNAPSHOT_FORMAT = 1
_ENGINE_REVISION = "simulation-v1"
_SUPPORTED_ENGINE_REVISIONS = {_ENGINE_REVISION}
_SUPPORTED_RULES_REVISIONS = {"a-provisional-1"}


class IdempotencyConflictError(DomainError):
    """The same idempotency key was already used for a different command."""

    code = "idempotency_key_conflict"


class RunAccessDeniedError(DomainError):
    """The supplied bearer token does not grant access to this run."""

    code = "run_token_invalid"


@dataclass(frozen=True, slots=True)
class RunSnapshot:
    """Versioned mutable snapshot envelope, including objective progress outside RunState."""

    run: Run
    goals: tuple[GoalProgress, ...]

    def encode(self) -> dict[str, object]:
        return {
            "format_version": _SNAPSHOT_FORMAT,
            "run": encode_run(self.run),
            "goals": [
                {"goal_id": item.goal_id, "status": item.status.value} for item in self.goals
            ],
        }

    @classmethod
    def decode(cls, value: object) -> RunSnapshot:
        if not isinstance(value, dict) or set(value) != {"format_version", "run", "goals"}:
            raise InvalidValueError("invalid run snapshot envelope")
        if type(value["format_version"]) is not int or value["format_version"] != _SNAPSHOT_FORMAT:
            raise InvalidValueError("unsupported run snapshot format")
        raw_goals = value["goals"]
        if not isinstance(raw_goals, list):
            raise InvalidValueError("run snapshot goals must be a list")
        goals: list[GoalProgress] = []
        for item in raw_goals:
            if not isinstance(item, dict) or set(item) != {"goal_id", "status"}:
                raise InvalidValueError("invalid goal progress in run snapshot")
            try:
                goals.append(GoalProgress(item["goal_id"], GoalStatus(item["status"])))
            except (TypeError, ValueError) as error:
                raise InvalidValueError("invalid goal progress in run snapshot") from error
        if len({item.goal_id for item in goals}) != len(goals):
            raise InvalidValueError("goal progress IDs must be unique in a run snapshot")
        return cls(decode_run(value["run"]), tuple(goals))


def _validate_record_snapshot(
    record: ports.RunRecord,
    snapshot: RunSnapshot,
    captured: CapturedSeason,
) -> None:
    run = snapshot.run
    if (
        run.id != record.run_id
        or run.season_id != record.playable_season_id
        or run.seed != record.seed
        or run.status.value != record.status.value
    ):
        raise InvalidValueError("run snapshot identity or status does not match its record")
    run_log = tuple(
        (item.sequence, item.block_id, item.dilemma_id, item.option_id)
        for item in run.decisions
    )
    stored_log = tuple(
        (item.sequence, item.block_id, item.dilemma_id, item.option_id)
        for item in record.decisions
    )
    if run_log != stored_log:
        raise InvalidValueError("run snapshot decisions do not match the append-only log")
    expected_goals = tuple(goal.goal_id for goal in captured.goals)
    actual_goals = tuple(item.goal_id for item in snapshot.goals)
    if actual_goals != expected_goals:
        raise InvalidValueError("run snapshot goal progress does not match captured objectives")
    try:
        initial_data = json.loads(record.replay_inputs.initial_state_json)
        initial = RunSnapshot.decode(initial_data)
    except (json.JSONDecodeError, InvalidValueError) as error:
        raise InvalidValueError("initial state snapshot is invalid") from error
    initial_run = initial.run
    if (
        initial_run.id != record.run_id
        or initial_run.season_id != record.playable_season_id
        or initial_run.seed != record.seed
        or initial_run.status.value != "in_progress"
        or initial_run.block_index != 0
        or initial_run.run_state != captured.initial_state
        or initial_run.blocks != captured.run_blocks
        or initial_run.decisions
        or initial_run.block_records
        or initial_run.cursor is not None
        or tuple((item.goal_id, item.status) for item in initial.goals)
        != tuple((goal.goal_id, GoalStatus.PENDING) for goal in captured.goals)
    ):
        raise InvalidValueError("initial state snapshot does not match captured run inputs")


def _validate_revisions(record: ports.RunRecord) -> RulesConfiguration:
    rules = RulesConfiguration.from_json(record.replay_inputs.rules_configuration_json)
    record.replay_inputs.ensure_compatible(
        engine_revisions=_SUPPORTED_ENGINE_REVISIONS,
        rules_revisions=_SUPPORTED_RULES_REVISIONS,
    )
    if rules.revision != record.replay_inputs.rules_revision:
        raise InvalidValueError("rules configuration revision does not match replay metadata")
    return rules


@dataclass(frozen=True, slots=True)
class RunView:
    run: Run
    goals: tuple[GoalProgress, ...]
    version: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class StartedRun:
    run_id: RunId
    token: str
    view: RunView


@dataclass(frozen=True, slots=True)
class _DecisionCommand:
    run_id: RunId
    token: str
    idempotency_key: str
    request_hash: str
    expected_version: int
    dilemma_id: DilemmaId
    option_id: OptionId


def _canonical_json(value: object) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def _view(record: ports.RunRecord) -> RunView:
    snapshot = RunSnapshot.decode(record.snapshot)
    return RunView(
        snapshot.run, snapshot.goals, record.version, record.created_at, record.updated_at
    )


def _record_status(run: Run) -> ports.RunStatus:
    return ports.RunStatus(run.status.value)


def _request_hash(
    dilemma_id: DilemmaId, option_id: OptionId, expected_version: int
) -> str:
    payload = _canonical_json(
        {
            "operation": "take_decision",
            "dilemma_id": dilemma_id.value,
            "option_id": option_id.value,
            "expected_version": expected_version,
        }
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class StartRun:
    """Capture one season and atomically create its immutable replay inputs and initial state."""

    def __init__(  # noqa: PLR0913 - explicit injected application dependencies
        self,
        *,
        uow: ports.UnitOfWork,
        capture_game: Callable[[PlayableSeasonId, RulesConfiguration], CapturedSeason],
        clock: Clock,
        event_bus: EventBus,
        token_generator: ports.RunTokenGenerator,
        token_hasher: ports.RunTokenHasher,
        seed_factory: Callable[[], Seed],
        run_id_factory: Callable[[], RunId] = RunId.new,
        rules: RulesConfiguration,
    ) -> None:
        self._uow = uow
        self._capture_game = capture_game
        self._clock = clock
        self._event_bus = event_bus
        self._token_generator = token_generator
        self._token_hasher = token_hasher
        self._seed_factory = seed_factory
        self._run_id_factory = run_id_factory
        if rules.revision not in _SUPPORTED_RULES_REVISIONS:
            raise InvalidValueError("rules revision is not supported for new runs")
        self._rules = rules

    def execute(self, season_id: PlayableSeasonId) -> StartedRun:
        captured = self._capture_game(season_id, self._rules)
        if captured.playable_season_id != season_id:
            raise InvalidValueError("captured season identity does not match request")
        now = self._clock.now()
        run_id, seed = self._run_id_factory(), self._seed_factory()
        run, events = Run.start(
            run_id,
            season_id,
            seed,
            captured.initial_state,
            captured.run_blocks,
            now,
        )
        initial = RunSnapshot(
            run,
            tuple(GoalProgress(goal.goal_id, GoalStatus.PENDING) for goal in captured.goals),
        )
        initial_json = _canonical_json(initial.encode())
        replay_inputs = ReplayInputs(
            captured.snapshot,
            initial_json,
            self._rules.canonical_json(),
            _ENGINE_REVISION,
            self._rules.revision,
        )
        token = self._token_generator.generate()
        record = ports.RunRecord(
            run_id,
            season_id,
            seed,
            self._token_hasher.hash(token),
            0,
            ports.RunStatus.IN_PROGRESS,
            initial.encode(),
            (),
            now,
            now,
            replay_inputs,
        )
        with self._uow as uow:
            uow.runs.add(record)
            uow.commit()
        for event in events:
            self._event_bus.publish(event)
        return StartedRun(run_id, token, _view(record))


class GetRun:
    """Read and authenticate a persisted run without exposing its token hash."""

    def __init__(
        self,
        *,
        uow: ports.UnitOfWork,
        token_hasher: ports.RunTokenHasher,
        restore_game: Callable[[RunContentSnapshot, RulesConfiguration], CapturedSeason],
    ) -> None:
        self._uow = uow
        self._token_hasher = token_hasher
        self._restore_game = restore_game

    def execute(self, run_id: RunId, token: str) -> RunView:
        with self._uow as uow:
            record = uow.runs.get(run_id)
        if record is None:
            raise ports.RunNotFoundError(run_id)
        if not self._token_hasher.verify(token, record.run_token_hash):
            raise RunAccessDeniedError("invalid run token")
        rules = _validate_revisions(record)
        snapshot = RunSnapshot.decode(record.snapshot)
        captured = self._restore_game(record.replay_inputs.content, rules)
        _validate_record_snapshot(record, snapshot, captured)
        return RunView(
            snapshot.run, snapshot.goals, record.version, record.created_at, record.updated_at
        )


class TakeDecision:
    """Apply a captured option and append it atomically with its idempotent response."""

    def __init__(
        self,
        *,
        uow: ports.UnitOfWork,
        clock: Clock,
        event_bus: EventBus,
        token_hasher: ports.RunTokenHasher,
        restore_game: Callable[[RunContentSnapshot, RulesConfiguration], CapturedSeason],
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._event_bus = event_bus
        self._token_hasher = token_hasher
        self._restore_game = restore_game

    def execute(  # noqa: PLR0913, PLR0917 - command fields mirror the durable request body
        self,
        run_id: RunId,
        token: str,
        idempotency_key: str,
        expected_version: int,
        dilemma_id: DilemmaId,
        option_id: OptionId,
    ) -> RunView:
        request_hash = _request_hash(dilemma_id, option_id, expected_version)
        command = _DecisionCommand(
            run_id,
            token,
            idempotency_key,
            request_hash,
            expected_version,
            dilemma_id,
            option_id,
        )
        try:
            result, events = self._execute_once(command)
        except (ports.ConcurrencyError, ports.IdempotencyKeyExistsError):
            stored = self._read_idempotency(
                command.run_id, command.token, command.idempotency_key
            )
            if stored is None:
                raise
            if stored.request_hash != command.request_hash:
                raise IdempotencyConflictError(
                    "idempotency key belongs to a different command"
                ) from None
            return _view_from_response(stored.response)
        for event in events:
            self._event_bus.publish(event)
        return result

    def _execute_once(
        self,
        command: _DecisionCommand,
    ) -> tuple[RunView, tuple[DomainEvent, ...]]:
        now = self._clock.now()
        with self._uow as uow:
            run_id = command.run_id
            record = uow.runs.get(command.run_id)
            if record is None:
                raise ports.RunNotFoundError(run_id)
            self._require_token(command.token, record)
            if type(command.expected_version) is not int or command.expected_version < 0:
                raise InvalidValueError("expected_version must be a non-negative integer")
            snapshot = RunSnapshot.decode(record.snapshot)
            rules = _validate_revisions(record)
            captured = self._restore_game(record.replay_inputs.content, rules)
            _validate_record_snapshot(record, snapshot, captured)
            existing = uow.runs.get_idempotent(run_id, command.idempotency_key)
            if existing is not None:
                if existing.request_hash != command.request_hash:
                    raise IdempotencyConflictError("idempotency key belongs to a different command")
                return _view_from_response(existing.response), ()

            if record.version != command.expected_version:
                raise ports.ConcurrencyError(run_id, expected=command.expected_version)
            current_block = captured.blocks[snapshot.run.block_index]
            dilemma = next(
                (item for item in current_block.dilemmas if item.id == command.dilemma_id), None
            )
            if dilemma is None:
                raise InvalidValueError("dilemma does not belong to the current block")
            option = next((item for item in dilemma.options if item.id == command.option_id), None)
            if option is None:
                raise InvalidValueError("option does not belong to the selected dilemma")
            validated, events = snapshot.run.take_decision(
                command.dilemma_id, command.option_id, now
            )
            resulting_state: RunState = snapshot.run.run_state
            for effect in option.effects:
                resulting_state = effects.apply(effect, resulting_state, on=current_block.start)
            changed = replace(validated, run_state=resulting_state)
            updated_snapshot = RunSnapshot(changed, snapshot.goals)
            updated = ports.RunRecord(
                record.run_id,
                record.playable_season_id,
                record.seed,
                record.run_token_hash,
                record.version + 1,
                _record_status(changed),
                updated_snapshot.encode(),
                (
                    *record.decisions,
                    ports.DecisionRecord(
                        len(record.decisions) + 1,
                        current_block.id,
                        command.dilemma_id,
                        command.option_id,
                        now,
                    ),
                ),
                record.created_at,
                now,
                record.replay_inputs,
            )
            response = _response_json(updated)
            uow.runs.save(updated, record.version)
            uow.runs.put_idempotent(
                ports.IdempotencyRecord(
                    run_id, command.idempotency_key, command.request_hash, response, now
                )
            )
            uow.commit()
        return _view(updated), cast("tuple[DomainEvent, ...]", events)

    def _read_idempotency(
        self, run_id: RunId, token: str, key: str
    ) -> ports.IdempotencyRecord | None:
        with self._uow as uow:
            record = uow.runs.get(run_id)
            if record is None:
                raise ports.RunNotFoundError(run_id)
            self._require_token(token, record)
            return uow.runs.get_idempotent(run_id, key)

    def _require_token(self, token: str, record: ports.RunRecord) -> None:
        if not self._token_hasher.verify(token, record.run_token_hash):
            raise RunAccessDeniedError("invalid run token")


def _response_json(record: ports.RunRecord) -> Mapping[str, object]:
    return {
        "run_id": str(record.run_id),
        "version": record.version,
        "snapshot": record.snapshot,
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
    }


def _view_from_response(value: Mapping[str, object]) -> RunView:
    try:
        snapshot = RunSnapshot.decode(value["snapshot"])
        version = value["version"]
        if type(version) is not int:
            raise TypeError
        created_at = datetime.fromisoformat(cast("str", value["created_at"]))
        updated_at = datetime.fromisoformat(cast("str", value["updated_at"]))
    except (KeyError, TypeError, ValueError, InvalidValueError) as error:
        raise InvalidValueError("stored idempotent response is invalid") from error
    return RunView(snapshot.run, snapshot.goals, version, created_at, updated_at)
