"""Contract of `RatingSheetStore`: what every implementation (fake and YAML) must satisfy.

The content under `backend/tests/fixtures/content/` is the shared data: Test FC 2000-01.
"""

import pytest

from mister.catalog.application.ratings_tool import (
    ClubSeasonRatingsUnavailableError,
    PlayerNotInSquadError,
    RatingSheetStore,
)
from mister.catalog.domain.ratings import LevelTier

CLUB_SEASON = "test-fc-2000-01"
OVERRIDDEN = "tfc-03"


class RatingSheetStoreContract:
    @pytest.fixture
    def store(self) -> RatingSheetStore:
        raise NotImplementedError

    def test_it_loads_the_club_data_and_every_player(self, store: RatingSheetStore) -> None:
        sheet = store.load(CLUB_SEASON)

        assert sheet.club_season == CLUB_SEASON
        assert sheet.club.level_tier is LevelTier.B
        assert len(sheet.players) == 22
        assert sheet.players[0].player_id == "tfc-01"
        assert sheet.players[0].stats.minutes_all is not None

    def test_it_loads_the_override_value_of_an_overridden_player(
        self, store: RatingSheetStore
    ) -> None:
        players = {p.player_id: p for p in store.load(CLUB_SEASON).players}

        override = players[OVERRIDDEN].override_value
        assert override is not None
        assert players[OVERRIDDEN].stored_rating == override
        assert players["tfc-01"].override_value is None

    def test_it_fails_for_an_unknown_club_season(self, store: RatingSheetStore) -> None:
        with pytest.raises(ClubSeasonRatingsUnavailableError):
            store.load("nowhere-fc-2000-01")

    def test_saved_ratings_are_loaded_back(self, store: RatingSheetStore) -> None:
        before = {p.player_id: p.stored_rating for p in store.load(CLUB_SEASON).players}

        store.save(CLUB_SEASON, {"tfc-01": 55, "tfc-02": None})

        after = {p.player_id: p.stored_rating for p in store.load(CLUB_SEASON).players}
        assert after["tfc-01"] == 55
        assert after["tfc-02"] is None
        assert {k: v for k, v in after.items() if k not in {"tfc-01", "tfc-02"}} == {
            k: v for k, v in before.items() if k not in {"tfc-01", "tfc-02"}
        }

    def test_it_refuses_to_save_the_rating_of_a_player_that_is_not_in_the_squad(
        self, store: RatingSheetStore
    ) -> None:
        with pytest.raises(PlayerNotInSquadError):
            store.save(CLUB_SEASON, {"nobody": 50})
