"""In-memory `HistoricalOutcomeProvider`, built from DTOs."""

from collections.abc import Iterable

from mister.evaluation.application.ports import (
    HistoricalOutcomeNotFoundError,
    HistoricalSeasonOutcome,
)
from mister.shared_kernel.ids import PlayableSeasonId


class InMemoryHistoricalOutcomeProvider:
    """Serves the outcomes it was built with."""

    def __init__(self, outcomes: Iterable[HistoricalSeasonOutcome] = ()) -> None:
        self._outcomes = {outcome.season_id: outcome for outcome in outcomes}

    def get_historical_outcome(self, season_id: PlayableSeasonId) -> HistoricalSeasonOutcome:
        try:
            return self._outcomes[season_id]
        except KeyError:
            raise HistoricalOutcomeNotFoundError(season_id) from None
