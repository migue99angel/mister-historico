"""Invariants of the Catalog published language (DTOs of `catalog.application.api`)."""

from dataclasses import FrozenInstanceError, replace
from typing import assert_never

import pytest
from tests.contracts.suites.sample_content import make_sample_season

from mister.catalog.application.api import (
    BoardConfidenceEffectDTO,
    CompetitionPriorityEffectDTO,
    EffectDTO,
    FitnessEffectDTO,
    InjuryEffectDTO,
    MoraleEffectDTO,
    PlayableSeasonNotFoundError,
    PlayerMoraleEffectDTO,
    Round,
    SellPlayerEffectDTO,
    SetTacticEffectDTO,
    SignPlayerEffectDTO,
    StageDTO,
    YouthMinutesEffectDTO,
)
from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import ClubSeasonId, OptionId, PlayableSeasonId


def _describe(effect: EffectDTO) -> str:
    """Exhaustive `match` over the closed union: mypy fails if a type is missing."""
    match effect:
        case MoraleEffectDTO():
            name = "morale"
        case PlayerMoraleEffectDTO():
            name = "player_morale"
        case SignPlayerEffectDTO():
            name = "sign_player"
        case SellPlayerEffectDTO():
            name = "sell_player"
        case SetTacticEffectDTO():
            name = "set_tactic"
        case CompetitionPriorityEffectDTO():
            name = "competition_priority"
        case BoardConfidenceEffectDTO():
            name = "board_confidence"
        case YouthMinutesEffectDTO():
            name = "youth_minutes"
        case InjuryEffectDTO():
            name = "injury"
        case FitnessEffectDTO():
            name = "fitness"
        case _ as unreachable:
            assert_never(unreachable)
    return name


def test_effect_union_covers_the_ten_types_of_the_dsl() -> None:
    season = make_sample_season()

    kinds = {
        _describe(effect)
        for dilemma in season.dilemmas
        for option in dilemma.options
        for effect in option.effects
    }

    assert kinds == {
        "morale",
        "player_morale",
        "sign_player",
        "sell_player",
        "set_tactic",
        "competition_priority",
        "board_confidence",
        "youth_minutes",
        "injury",
        "fitness",
    }


def test_dtos_are_immutable() -> None:
    season = make_sample_season()

    with pytest.raises(FrozenInstanceError):
        season.season = "1999-00"  # type: ignore[misc]


def test_own_club_season_is_the_one_the_season_points_to() -> None:
    season = make_sample_season()

    assert season.own_club_season.id == season.club_season_id


def test_a_season_must_include_its_own_club_season() -> None:
    season = make_sample_season()

    with pytest.raises(InvalidValueError, match="own club season"):
        replace(season, club_season_id=ClubSeasonId("ghost-2000-01"))


def test_a_club_season_has_a_squad_or_an_aggregate_never_both_or_neither() -> None:
    own = make_sample_season().own_club_season
    minnow = make_sample_season().club_seasons[2]

    with pytest.raises(InvalidValueError, match="squad or an aggregate"):
        replace(own, aggregate=minnow.aggregate)
    with pytest.raises(InvalidValueError, match="squad or an aggregate"):
        replace(own, squad=None)


def test_a_league_needs_its_rules_and_no_stages() -> None:
    league = make_sample_season().competitions[0]

    with pytest.raises(InvalidValueError, match="league"):
        replace(league, league=None)
    with pytest.raises(InvalidValueError, match="league"):
        replace(league, stages=(StageDTO("x", "X", Round.FINAL, 1, False, False, False),))


def test_a_knockout_competition_needs_stages_and_no_league_rules() -> None:
    season = make_sample_season()
    league, cup = season.competitions[0], season.competitions[1]

    with pytest.raises(InvalidValueError, match="stages"):
        replace(cup, stages=())
    with pytest.raises(InvalidValueError, match="stages"):
        replace(cup, league=league.league)


def test_a_dilemma_historical_option_must_be_one_of_its_options() -> None:
    dilemma = make_sample_season().dilemmas[0]

    with pytest.raises(InvalidValueError, match="historical option"):
        replace(dilemma, historical_option=OptionId("zzz"))


def test_season_not_found_error_has_a_stable_code() -> None:
    error = PlayableSeasonNotFoundError(PlayableSeasonId("a-2000-01"))

    assert error.code == "season_not_found"
    assert "a-2000-01" in str(error)


def test_summary_is_built_from_the_own_club_season() -> None:
    season = make_sample_season()

    summary = season.summary()

    assert (summary.club_name, summary.short_name) == ("Test FC", "TES")
