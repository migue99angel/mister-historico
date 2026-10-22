"""In-memory `SeasonContentProvider`, built directly from DTOs (tests and local runs)."""

from collections.abc import Iterable, Sequence

from mister.catalog.application.api import (
    PlayableSeasonDTO,
    PlayableSeasonNotFoundError,
    PlayableSeasonSummaryDTO,
)
from mister.shared_kernel.ids import PlayableSeasonId


class InMemorySeasonContentProvider:
    """Serves the seasons it was built with; it never maps from content files."""

    def __init__(self, seasons: Iterable[PlayableSeasonDTO] = ()) -> None:
        self._seasons = {season.id: season for season in seasons}

    def list_playable_seasons(self) -> Sequence[PlayableSeasonSummaryDTO]:
        ordered = sorted(self._seasons.values(), key=lambda season: season.id.value)
        return tuple(season.summary() for season in ordered)

    def get_playable_season(self, season_id: PlayableSeasonId) -> PlayableSeasonDTO:
        try:
            return self._seasons[season_id]
        except KeyError:
            raise PlayableSeasonNotFoundError(season_id) from None
