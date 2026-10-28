import json

import pytest

from mister.game.application.rules import InitialStateRules, PlayerEligibilityRules, RulesConfiguration
from mister.game.domain.board import BoardRules
from mister.game.domain.morale import MoraleRules
from mister.shared_kernel.errors import InvalidValueError


def test_rules_configuration_serializes_every_parameter_canonically() -> None:
    rules = RulesConfiguration(BoardRules(20, 3, 0, -3, 10, -10), MoraleRules(2, 0, -2, 85, 90, -3), InitialStateRules(50, 50, 100, 50, "normal", "block_start"), PlayerEligibilityRules(True, True, True, True, 1), "profile-1")
    payload = rules.canonical_json()
    assert json.loads(payload)["board"]["sacking_threshold"] == 20
    assert json.loads(payload)["eligibility"]["exempt_players_signed_during_block"] is True
    assert payload == rules.canonical_json()


def test_approved_a_profile_is_explicit_and_uses_expected_values() -> None:
    profile = RulesConfiguration.a_profile()
    assert profile.board.win_delta == 3 and profile.board.loss_delta == -3
    assert profile.morale.star_rating_threshold == 85 and profile.morale.minimum_minutes == 90
    assert profile.initial_state.player_fitness == 100
    assert profile.eligibility.require_membership_at_block_start


def test_configuration_rejects_missing_revision_or_implicit_decision_date() -> None:
    with pytest.raises(InvalidValueError):
        InitialStateRules(50, 50, 100, 50, "normal", "now")
    with pytest.raises(InvalidValueError):
        RulesConfiguration(BoardRules(20, 3, 0, -3, 10, -10), MoraleRules(2, 0, -2, 85, 90, -3), InitialStateRules(50, 50, 100, 50, "normal", "block_start"), PlayerEligibilityRules(True, True, True, True, 1), " ")
