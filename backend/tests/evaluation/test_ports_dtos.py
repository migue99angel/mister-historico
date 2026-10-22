"""Invariants of the Evaluation port DTOs."""

import pytest

from mister.evaluation.application.ports import (
    CompetitionHistory,
    CompetitionKind,
    CompetitionTier,
    HistoricalOutcomeNotFoundError,
    ObjectiveKind,
)
from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import CompetitionId, PlayableSeasonId


def test_the_not_found_error_has_a_stable_code_and_names_the_season() -> None:
    error = HistoricalOutcomeNotFoundError(PlayableSeasonId("a-2000-01"))

    assert error.code == "season_not_found"
    assert "a-2000-01" in str(error)


def test_a_champion_cannot_have_been_eliminated() -> None:
    with pytest.raises(InvalidValueError, match="champion"):
        CompetitionHistory(
            CompetitionId("copa-test"),
            "Copa Test",
            CompetitionKind.CUP,
            CompetitionTier.DOMESTIC_CUP,
            champion=True,
            eliminated_in_stage_id="final",
            eliminated_in_stage_name="Final",
        )


def test_the_stage_of_an_elimination_has_an_id_and_a_name_or_neither() -> None:
    with pytest.raises(InvalidValueError, match="stage"):
        CompetitionHistory(
            CompetitionId("copa-test"),
            "Copa Test",
            CompetitionKind.CUP,
            CompetitionTier.DOMESTIC_CUP,
            champion=False,
            eliminated_in_stage_id="final",
        )


def test_the_vocabulary_matches_the_content_format() -> None:
    assert {k.value for k in CompetitionKind} == {"league", "cup", "super_cup", "continental_cup"}
    assert {t.value for t in CompetitionTier} == {
        "domestic_league",
        "domestic_cup",
        "domestic_super_cup",
        "continental_primary",
        "continental_secondary",
    }
    assert {o.value for o in ObjectiveKind} == {"win", "finish_top", "reach_stage"}
