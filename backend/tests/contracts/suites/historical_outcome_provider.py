"""Contract of the Evaluation `HistoricalOutcomeProvider` port.

Reuse: subclass `HistoricalOutcomeProviderContract` and override `make_provider` with a factory
that returns a provider serving exactly the given outcomes (a Catalog-backed ACL adapter loads
the matching season first).
"""

from collections.abc import Callable, Sequence

import pytest

from mister.evaluation.application.ports import (
    BoardObjectiveSpec,
    CompetitionHistory,
    CompetitionKind,
    CompetitionTier,
    HistoricalOutcomeNotFoundError,
    HistoricalOutcomeProvider,
    HistoricalSeasonOutcome,
    ObjectiveKind,
)
from mister.shared_kernel.errors import DomainError
from mister.shared_kernel.ids import CompetitionId, PlayableSeasonId

ProviderFactory = Callable[[Sequence[HistoricalSeasonOutcome]], HistoricalOutcomeProvider]


def make_outcome(slug: str = "test-fc-2000-01") -> HistoricalSeasonOutcome:
    return HistoricalSeasonOutcome(
        season_id=PlayableSeasonId(slug),
        club_name="Test FC",
        manager_display_name="Mister Ficticio",
        manager_alias_name="El Profesor",
        competitions=(
            CompetitionHistory(
                CompetitionId("liga-test"),
                "Liga Test",
                CompetitionKind.LEAGUE,
                CompetitionTier.DOMESTIC_LEAGUE,
                champion=False,
                final_position=2,
            ),
            CompetitionHistory(
                CompetitionId("copa-test"),
                "Copa Test",
                CompetitionKind.CUP,
                CompetitionTier.DOMESTIC_CUP,
                champion=True,
            ),
            CompetitionHistory(
                CompetitionId("copa-continental-test"),
                "Copa Continental Test",
                CompetitionKind.CONTINENTAL_CUP,
                CompetitionTier.CONTINENTAL_PRIMARY,
                champion=False,
                eliminated_in_stage_id="groups",
                eliminated_in_stage_name="Group stage",
            ),
        ),
        board_objectives=(
            BoardObjectiveSpec(
                "obj-liga",
                CompetitionId("liga-test"),
                ObjectiveKind.FINISH_TOP,
                "Finish top three.",
                target_position=3,
            ),
            BoardObjectiveSpec(
                "obj-copa",
                CompetitionId("copa-test"),
                ObjectiveKind.REACH_STAGE,
                "Reach the final.",
                target_stage="final",
            ),
            BoardObjectiveSpec(
                "obj-cont", CompetitionId("copa-continental-test"), ObjectiveKind.WIN, "Win it."
            ),
        ),
    )


class HistoricalOutcomeProviderContract:
    """Behaviour every `HistoricalOutcomeProvider` must have."""

    @pytest.fixture
    def make_provider(self) -> ProviderFactory:
        raise NotImplementedError

    def test_it_returns_the_outcome_it_was_given(self, make_provider: ProviderFactory) -> None:
        outcome = make_outcome()

        assert make_provider([outcome]).get_historical_outcome(outcome.season_id) == outcome

    def test_it_picks_the_requested_season(self, make_provider: ProviderFactory) -> None:
        first, second = make_outcome("test-fc-2000-01"), make_outcome("mock-city-2001-02")

        provider = make_provider([first, second])

        assert provider.get_historical_outcome(second.season_id) == second

    def test_an_unknown_season_raises_a_domain_error_with_its_code(
        self, make_provider: ProviderFactory
    ) -> None:
        provider = make_provider([make_outcome()])

        with pytest.raises(HistoricalOutcomeNotFoundError) as caught:
            provider.get_historical_outcome(PlayableSeasonId("nobody-1999-00"))

        assert isinstance(caught.value, DomainError)
        assert caught.value.code == "season_not_found"
