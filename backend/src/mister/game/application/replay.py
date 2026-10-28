"""Authenticate and reconstruct a durable run using its captured inputs only."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from mister.game.application import ports
from mister.game.application.closure import advance_snapshot
from mister.game.application.use_cases import (
    RunAccessDeniedError,
    RunSnapshot,
    _load_snapshot,
    apply_choice,
)
from mister.game.domain.run import RunStatus
from mister.shared_kernel.errors import InvalidValueError

if TYPE_CHECKING:
    from collections.abc import Callable

    from mister.game.application.content_model import CapturedSeason
    from mister.game.application.rules import RulesConfiguration
    from mister.game.application.run_content import RunContentSnapshot
    from mister.shared_kernel.ids import BlockId, RunId


@dataclass(frozen=True, slots=True)
class ReplayResult:
    """A verified reconstruction, kept separate from client-facing run views."""

    run_id: RunId
    verified: bool
    reconstructed: RunSnapshot


class ReplayRun:
    """Rebuild persisted decisions and closures without mutating the run or publishing events."""

    def __init__(
        self,
        *,
        uow: ports.UnitOfWork,
        token_hasher: ports.RunTokenHasher,
        restore_game: Callable[[RunContentSnapshot, RulesConfiguration], CapturedSeason],
        simulator: ports.SeasonSimulator,
    ) -> None:
        self._uow = uow
        self._token_hasher = token_hasher
        self._restore_game = restore_game
        self._simulator = simulator

    def execute(self, run_id: RunId, token: str) -> ReplayResult:
        """Authenticate, reconstruct the snapshot and reject any deterministic mismatch."""
        with self._uow as uow:
            record = uow.runs.get(run_id)
        if record is None:
            raise ports.RunNotFoundError(run_id)
        if not self._token_hasher.verify(token, record.run_token_hash):
            raise RunAccessDeniedError("invalid run token")

        target, captured, rules = _load_snapshot(record, self._restore_game)
        initial_payload = json.loads(record.replay_inputs.initial_state_json)
        reconstructed = RunSnapshot.decode(initial_payload)
        decisions_by_block: dict[BlockId, list[ports.DecisionRecord]] = {}
        for decision in record.decisions:
            decisions_by_block.setdefault(decision.block_id, []).append(decision)

        applied_sequences: set[int] = set()
        closed_count = len(target.run.block_records)
        for block_index in range(closed_count):
            if reconstructed.run.status is not RunStatus.IN_PROGRESS:
                raise InvalidValueError("replay closed blocks after the run became terminal")
            block_id = reconstructed.run.blocks[block_index].id
            if reconstructed.run.block_index != block_index:
                raise InvalidValueError("replay block cursor does not match its closed prefix")
            reconstructed = self._apply_logged_decisions(
                reconstructed,
                captured,
                decisions_by_block.get(block_id, ()),
                applied_sequences,
            )
            reconstructed, _events = advance_snapshot(
                reconstructed,
                captured,
                self._simulator,
                rules,
                record.updated_at,
            )

        if reconstructed.run.status is RunStatus.IN_PROGRESS:
            current_block = reconstructed.run.current_block
            if current_block is None:
                raise InvalidValueError("an in-progress replay has no current block")
            reconstructed = self._apply_logged_decisions(
                reconstructed,
                captured,
                decisions_by_block.get(current_block, ()),
                applied_sequences,
            )

        if applied_sequences != {decision.sequence for decision in record.decisions}:
            raise InvalidValueError("replay did not consume every logged decision")
        if reconstructed != target:
            raise InvalidValueError("replayed run does not match the persisted snapshot")
        return ReplayResult(run_id, True, reconstructed)

    @staticmethod
    def _apply_logged_decisions(
        snapshot: RunSnapshot,
        captured: CapturedSeason,
        decisions: tuple[ports.DecisionRecord, ...] | list[ports.DecisionRecord],
        applied_sequences: set[int],
    ) -> RunSnapshot:
        result = snapshot
        for decision in decisions:
            if decision.sequence in applied_sequences:
                raise InvalidValueError("replay encountered a duplicate decision sequence")
            result, _events = apply_choice(
                result,
                captured,
                decision.dilemma_id,
                decision.option_id,
                decision.decided_at,
            )
            applied_sequences.add(decision.sequence)
        return result
