"""The closed effect DSL: a discriminated union on `type` with bounded deltas."""

from datetime import date
from typing import Any

import pytest
from pydantic import TypeAdapter, ValidationError

from mister.catalog.infrastructure.content_schema.effects import (
    BoardConfidenceEffect,
    CompetitionPriorityEffect,
    Effect,
    FitnessEffect,
    InjuryEffect,
    MoraleEffect,
    PlayerMoraleEffect,
    SellPlayerEffect,
    SetTacticEffect,
    SignPlayerEffect,
    YouthMinutesEffect,
)

_ADAPTER: TypeAdapter[Effect] = TypeAdapter(Effect)


def _parse(data: dict[str, Any]) -> Effect:
    return _ADAPTER.validate_python(data)


@pytest.mark.parametrize(
    ("data", "expected_type"),
    [
        ({"type": "morale", "delta": 5}, MoraleEffect),
        ({"type": "player_morale", "player_id": "p-1", "delta": -8}, PlayerMoraleEffect),
        ({"type": "sign_player", "player_id": "p-1"}, SignPlayerEffect),
        (
            {"type": "sign_player", "player_id": "p-1", "from_club_season": "rival-2000-01"},
            SignPlayerEffect,
        ),
        ({"type": "sell_player", "player_id": "p-1"}, SellPlayerEffect),
        (
            {"type": "sell_player", "player_id": "p-1", "to_club_season": "rival-2000-01"},
            SellPlayerEffect,
        ),
        ({"type": "set_tactic", "style": "pressing", "system": "4-3-3"}, SetTacticEffect),
        (
            {"type": "competition_priority", "competition_id": "cup", "priority": "high"},
            CompetitionPriorityEffect,
        ),
        ({"type": "board_confidence", "delta": -10}, BoardConfidenceEffect),
        ({"type": "youth_minutes", "player_id": "p-1"}, YouthMinutesEffect),
        (
            {"type": "injury", "player_id": "p-1", "date": date(2000, 12, 1), "days": 30},
            InjuryEffect,
        ),
        ({"type": "fitness", "delta": -10}, FitnessEffect),
        ({"type": "fitness", "delta": 10, "player_id": "p-1"}, FitnessEffect),
    ],
)
def test_each_effect_type_parses_to_its_model(data: dict[str, Any], expected_type: type) -> None:
    assert isinstance(_parse(data), expected_type)


def test_unknown_effect_type_is_rejected() -> None:
    with pytest.raises(ValidationError, match="union_tag_invalid"):
        _parse({"type": "teleport_player", "player_id": "p-1"})


def test_effect_with_unexpected_field_is_rejected() -> None:
    with pytest.raises(ValidationError, match="extra_forbidden"):
        _parse({"type": "morale", "delta": 5, "player_id": "p-1"})


@pytest.mark.parametrize(
    "data",
    [
        {"type": "morale", "delta": 21},
        {"type": "morale", "delta": -21},
        {"type": "player_morale", "player_id": "p-1", "delta": 31},
        {"type": "board_confidence", "delta": 26},
        {"type": "board_confidence", "delta": -26},
        {"type": "fitness", "delta": 31},
        {"type": "fitness", "delta": -31},
        {"type": "injury", "player_id": "p-1", "date": date(2000, 12, 1), "days": 0},
        {"type": "injury", "player_id": "p-1", "date": date(2000, 12, 1), "days": 366},
    ],
)
def test_out_of_range_effect_values_are_rejected(data: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        _parse(data)


@pytest.mark.parametrize("system", ["433", "4-3", "four-three-three", "4-3-3-"])
def test_set_tactic_rejects_malformed_systems(system: str) -> None:
    with pytest.raises(ValidationError, match="system"):
        _parse({"type": "set_tactic", "style": "balanced", "system": system})


def test_set_tactic_rejects_unknown_style() -> None:
    with pytest.raises(ValidationError, match="style"):
        _parse({"type": "set_tactic", "style": "parking-the-bus", "system": "4-4-2"})


def test_competition_priority_rejects_unknown_level() -> None:
    with pytest.raises(ValidationError, match="priority"):
        _parse({"type": "competition_priority", "competition_id": "cup", "priority": "max"})


def test_effects_are_immutable() -> None:
    effect = MoraleEffect(type="morale", delta=3)
    with pytest.raises(ValidationError, match="frozen"):
        effect.delta = 4  # type: ignore[misc]
