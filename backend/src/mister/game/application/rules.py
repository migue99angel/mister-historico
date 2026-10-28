"""Explicit, replayable balancing and eligibility rules for one game run."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, cast

from mister.game.domain.board import BoardRules
from mister.game.domain.morale import MoraleRules
from mister.shared_kernel.errors import InvalidValueError

_MAX_STATE_VALUE = 100


@dataclass(frozen=True, slots=True)
class InitialStateRules:
    """Required initial values and date policy for a new run."""

    team_morale: int
    player_morale: int
    player_fitness: int
    board_confidence: int
    initial_priority: str
    decision_date_policy: str

    def __post_init__(self) -> None:
        if any(
            type(value) is not int or not 0 <= value <= _MAX_STATE_VALUE
            for value in (
                self.team_morale,
                self.player_morale,
                self.player_fitness,
                self.board_confidence,
            )
        ):
            raise InvalidValueError("initial morale, fitness and confidence must be from 0 to 100")
        if self.initial_priority not in {"low", "normal", "high"}:
            raise InvalidValueError("initial priority is invalid")
        if self.decision_date_policy != "block_start":
            raise InvalidValueError("decision date policy must be explicit block_start")


@dataclass(frozen=True, slots=True)
class PlayerEligibilityRules:
    """Explicit criteria for counting a player as eligible for morale evaluation."""

    require_membership_at_block_start: bool
    require_membership_at_block_end: bool
    require_availability_for_all_fixtures: bool
    exempt_players_signed_during_block: bool
    minimum_team_fixtures: int

    def __post_init__(self) -> None:
        if any(
            type(value) is not bool
            for value in (
                self.require_membership_at_block_start,
                self.require_membership_at_block_end,
                self.require_availability_for_all_fixtures,
                self.exempt_players_signed_during_block,
            )
        ):
            raise InvalidValueError("eligibility criteria must be explicit booleans")
        if type(self.minimum_team_fixtures) is not int or self.minimum_team_fixtures < 0:
            raise InvalidValueError("minimum_team_fixtures must be non-negative")


@dataclass(frozen=True, slots=True)
class RulesConfiguration:
    """All values that affect initial state, board, morale or player eligibility."""

    board: BoardRules
    morale: MoraleRules
    initial_state: InitialStateRules
    eligibility: PlayerEligibilityRules
    revision: str

    def __post_init__(self) -> None:
        if not isinstance(self.board, BoardRules) or not isinstance(self.morale, MoraleRules):
            raise InvalidValueError("rules configuration requires BoardRules and MoraleRules")
        if not isinstance(self.initial_state, InitialStateRules) or not isinstance(
            self.eligibility, PlayerEligibilityRules
        ):
            raise InvalidValueError(
                "rules configuration requires initial-state and eligibility rules"
            )
        if not isinstance(self.revision, str) or not self.revision.strip():
            raise InvalidValueError("rules revision must not be blank")

    def canonical_json(self) -> str:
        """Return the complete configuration as canonical JSON for ReplayInputs."""
        payload = {
            "revision": self.revision,
            "board": {
                "sacking_threshold": self.board.sacking_threshold,
                "win_delta": self.board.win_delta,
                "draw_delta": self.board.draw_delta,
                "loss_delta": self.board.loss_delta,
                "objective_met_delta": self.board.objective_met_delta,
                "objective_missed_delta": self.board.objective_missed_delta,
            },
            "morale": {
                "win_delta": self.morale.win_delta,
                "draw_delta": self.morale.draw_delta,
                "loss_delta": self.morale.loss_delta,
                "star_rating_threshold": self.morale.star_rating_threshold,
                "minimum_minutes": self.morale.minimum_minutes,
                "unused_star_delta": self.morale.unused_star_delta,
            },
            "initial_state": {
                "team_morale": self.initial_state.team_morale,
                "player_morale": self.initial_state.player_morale,
                "player_fitness": self.initial_state.player_fitness,
                "board_confidence": self.initial_state.board_confidence,
                "initial_priority": self.initial_state.initial_priority,
                "decision_date_policy": self.initial_state.decision_date_policy,
            },
            "eligibility": {
                "require_membership_at_block_start": (
                    self.eligibility.require_membership_at_block_start
                ),
                "require_membership_at_block_end": self.eligibility.require_membership_at_block_end,
                "require_availability_for_all_fixtures": (
                    self.eligibility.require_availability_for_all_fixtures
                ),
                "exempt_players_signed_during_block": (
                    self.eligibility.exempt_players_signed_during_block
                ),
                "minimum_team_fixtures": self.eligibility.minimum_team_fixtures,
            },
        }
        return json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        )

    @classmethod
    def from_json(cls, value: str) -> RulesConfiguration:
        """Parse exactly the canonical rules schema; reject missing and unknown values."""
        try:
            payload = json.loads(
                value, object_pairs_hook=_unique_object, parse_constant=_reject_constant
            )
        except (json.JSONDecodeError, TypeError, ValueError) as error:
            raise InvalidValueError("invalid rules configuration JSON") from error
        if not isinstance(payload, dict) or set(payload) != {
            "revision",
            "board",
            "morale",
            "initial_state",
            "eligibility",
        }:
            raise InvalidValueError("rules configuration fields do not match the schema")
        try:
            result = cls(
                cast("Any", BoardRules)(
                    **_exact(
                        payload["board"],
                        {
                            "sacking_threshold",
                            "win_delta",
                            "draw_delta",
                            "loss_delta",
                            "objective_met_delta",
                            "objective_missed_delta",
                        },
                    )
                ),
                cast("Any", MoraleRules)(
                    **_exact(
                        payload["morale"],
                        {
                            "win_delta",
                            "draw_delta",
                            "loss_delta",
                            "star_rating_threshold",
                            "minimum_minutes",
                            "unused_star_delta",
                        },
                    )
                ),
                cast("Any", InitialStateRules)(
                    **_exact(
                        payload["initial_state"],
                        {
                            "team_morale",
                            "player_morale",
                            "player_fitness",
                            "board_confidence",
                            "initial_priority",
                            "decision_date_policy",
                        },
                    )
                ),
                cast("Any", PlayerEligibilityRules)(
                    **_exact(
                        payload["eligibility"],
                        {
                            "require_membership_at_block_start",
                            "require_membership_at_block_end",
                            "require_availability_for_all_fixtures",
                            "exempt_players_signed_during_block",
                            "minimum_team_fixtures",
                        },
                    )
                ),
                payload["revision"],
            )
        except (TypeError, KeyError) as error:
            raise InvalidValueError("invalid rules configuration values") from error
        if result.canonical_json() != value:
            raise InvalidValueError("rules configuration JSON must be canonical")
        return result

    @classmethod
    def a_profile(cls) -> RulesConfiguration:
        """The author's explicitly approved provisional profile for vertical slice A."""
        return cls(
            BoardRules(20, 3, 0, -3, 10, -10),
            MoraleRules(2, 0, -2, 85, 90, -3),
            InitialStateRules(50, 50, 100, 50, "normal", "block_start"),
            PlayerEligibilityRules(True, True, True, True, 1),
            "a-provisional-1",
        )


def _exact(value: object, keys: set[str]) -> dict[str, object]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise InvalidValueError("rules section fields do not match the schema")
    return dict(value)


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(token: str) -> object:
    raise ValueError(f"invalid JSON constant {token}")
