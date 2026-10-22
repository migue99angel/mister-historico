"""In-memory `RatingSheetStore` (tests and local runs)."""

from collections.abc import Iterable, Mapping
from dataclasses import replace

from mister.catalog.application.ratings_tool import (
    ClubSeasonRatings,
    ClubSeasonRatingsUnavailableError,
    PlayerNotInSquadError,
)


class InMemoryRatingSheetStore:
    """Serves the sheets it was built with and applies saved ratings to them.

    `saved` records the ratings of every `save` call, per club-season, so tests can check what
    was written.
    """

    def __init__(self, sheets: Iterable[ClubSeasonRatings] = ()) -> None:
        self._sheets = {sheet.club_season: sheet for sheet in sheets}
        self.saved: dict[str, dict[str, int | None]] = {}

    def load(self, club_season: str) -> ClubSeasonRatings:
        try:
            return self._sheets[club_season]
        except KeyError:
            raise ClubSeasonRatingsUnavailableError(
                f"{club_season} has no squad to compute ratings for"
            ) from None

    def save(self, club_season: str, ratings: Mapping[str, int | None]) -> None:
        sheet = self.load(club_season)
        known = {player.player_id for player in sheet.players}
        for player_id in ratings:
            if player_id not in known:
                raise PlayerNotInSquadError(club_season, player_id)
        players = tuple(
            replace(player, stored_rating=ratings[player.player_id])
            if player.player_id in ratings
            else player
            for player in sheet.players
        )
        self._sheets[club_season] = replace(sheet, players=players)
        self.saved.setdefault(club_season, {}).update(ratings)
