"""Catalog-to-Game ACL for capturing and restoring a run's immutable content."""

from mister.catalog.application.api import PlayableSeasonDTO, SeasonContentProvider
from mister.game.application.run_content import RunContentSnapshot
from mister.game.infrastructure.run_content_codec import (
    decode_playable_season,
    encode_playable_season,
)
from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import PlayableSeasonId


class CatalogRunContentAdapter:
    """Capture one published season exactly once and restore without consulting Catalog."""

    def __init__(self, provider: SeasonContentProvider) -> None:
        self._provider = provider

    def capture(self, season_id: PlayableSeasonId) -> RunContentSnapshot:
        season = self._provider.get_playable_season(season_id)
        if season.id != season_id:
            raise InvalidValueError("Catalog returned a different playable season identity")
        return encode_playable_season(season)

    @staticmethod
    def restore(snapshot: RunContentSnapshot) -> PlayableSeasonDTO:
        return decode_playable_season(snapshot)
