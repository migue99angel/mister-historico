"""Invariants of the Evaluation port DTOs."""

import pytest

from mister.evaluation.application.ports import (
    CompetitionHistory,
    HistoricalOutcomeNotFoundError,
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
            "cup",
            champion=True,
            eliminated_in_stage_name="Final",
        )
