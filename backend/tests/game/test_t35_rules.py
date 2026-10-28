import json

import pytest

from mister.game.application.rules import (
    InitialStateRules,
    PlayerEligibilityRules,
    RulesConfiguration,
)
from mister.game.domain.board import BoardRules
from mister.game.domain.morale import MoraleRules
from mister.shared_kernel.errors import InvalidValueError


def test_rules_configuration_serializes_every_parameter_canonically() -> None:
    rules = RulesConfiguration(
        BoardRules(20, 3, 0, -3, 10, -10),
        MoraleRules(2, 0, -2, 85, 90, -3),
        InitialStateRules(50, 50, 100, 50, "normal", "block_start"),
        PlayerEligibilityRules(True, True, True, True, 1),
        "profile-1",
    )
    payload = rules.canonical_json()
    assert json.loads(payload)["board"]["sacking_threshold"] == 20
    assert json.loads(payload)["eligibility"]["exempt_players_signed_during_block"] is True
    assert payload == rules.canonical_json()
    assert RulesConfiguration.from_json(payload) == rules


def test_approved_a_profile_is_explicit_and_uses_expected_values() -> None:
    profile = RulesConfiguration.a_profile()
    assert profile.board.win_delta == 3
    assert profile.board.loss_delta == -3
    assert profile.morale.star_rating_threshold == 85
    assert profile.morale.minimum_minutes == 90
    assert profile.initial_state.player_fitness == 100
    assert profile.eligibility.require_membership_at_block_start


def test_configuration_rejects_missing_revision_or_implicit_decision_date() -> None:
    with pytest.raises(InvalidValueError):
        InitialStateRules(50, 50, 100, 50, "normal", "now")
    with pytest.raises(InvalidValueError):
        RulesConfiguration(
            BoardRules(20, 3, 0, -3, 10, -10),
            MoraleRules(2, 0, -2, 85, 90, -3),
            InitialStateRules(50, 50, 100, 50, "normal", "block_start"),
            PlayerEligibilityRules(True, True, True, True, 1),
            " ",
        )
    with pytest.raises(InvalidValueError):
        RulesConfiguration.from_json(
            '{"revision":"x","board":{},"morale":{},"initial_state":{},"eligibility":{},"extra":1}'
        )


@pytest.mark.parametrize(
    "values",
    [
        (101, 50, 100, 50, "normal", "block_start"),
        (True, 50, 100, 50, "normal", "block_start"),
        (50, 50, 100, 50, "urgent", "block_start"),
        (50, 50, 100, 50, "normal", "after_match"),
    ],
)
def test_initial_state_rules_reject_invalid_ranges_types_and_policies(
    values: tuple[object, ...],
) -> None:
    with pytest.raises(InvalidValueError):
        InitialStateRules(*values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "criteria",
    [
        (True, True, True, 1, 0),
        (True, True, True, True, -1),
        (True, True, True, True, True),
    ],
)
def test_player_eligibility_rules_reject_non_boolean_and_negative_values(
    criteria: tuple[object, ...],
) -> None:
    with pytest.raises(InvalidValueError):
        PlayerEligibilityRules(*criteria)  # type: ignore[arg-type]


def test_configuration_rejects_incorrect_nested_value_types() -> None:
    with pytest.raises(InvalidValueError, match="BoardRules"):
        RulesConfiguration(
            object(),  # type: ignore[arg-type]
            MoraleRules(2, 0, -2, 85, 90, -3),
            InitialStateRules(50, 50, 100, 50, "normal", "block_start"),
            PlayerEligibilityRules(True, True, True, True, 1),
            "profile",
        )
    with pytest.raises(InvalidValueError, match="initial-state"):
        RulesConfiguration(
            BoardRules(20, 3, 0, -3, 10, -10),
            MoraleRules(2, 0, -2, 85, 90, -3),
            object(),  # type: ignore[arg-type]
            PlayerEligibilityRules(True, True, True, True, 1),
            "profile",
        )


@pytest.mark.parametrize(
    "payload",
    [
        "not json",
        "[]",
        '{"revision":"a","revision":"b"}',
        '{"revision":"a","board":NaN}',
        '{"revision":"x","board":{},"morale":{},"initial_state":{},"eligibility":{}}',
    ],
)
def test_rules_parser_rejects_malformed_json_duplicate_keys_and_wrong_envelopes(
    payload: str,
) -> None:
    with pytest.raises(InvalidValueError):
        RulesConfiguration.from_json(payload)


@pytest.mark.parametrize(
    ("section", "change"),
    [
        ("board", {"extra": 1}),
        ("morale", {"extra": 1}),
        ("initial_state", {"extra": 1}),
        ("eligibility", {"extra": 1}),
    ],
)
def test_rules_parser_rejects_unknown_nested_fields(
    section: str, change: dict[str, object]
) -> None:
    payload = json.loads(RulesConfiguration.a_profile().canonical_json())
    payload[section].update(change)

    with pytest.raises(InvalidValueError, match="section fields"):
        RulesConfiguration.from_json(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        )


def test_rules_parser_rejects_noncanonical_whitespace_and_non_string_revision() -> None:
    canonical = RulesConfiguration.a_profile().canonical_json()
    with pytest.raises(InvalidValueError, match="canonical"):
        RulesConfiguration.from_json(" " + canonical)
    payload = json.loads(canonical)
    payload["revision"] = ["a"]
    with pytest.raises(InvalidValueError):
        RulesConfiguration.from_json(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        )
