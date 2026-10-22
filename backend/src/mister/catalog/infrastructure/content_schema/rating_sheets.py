"""YAML adapter of `RatingSheetStore`: reads a squad file and rewrites only its ratings.

Reading uses the content schema (so the statistics are validated like anywhere else).
Writing uses `ruamel.yaml` in round-trip mode, which keeps comments, key order and the
formatting of everything it does not touch; a save that changes nothing leaves the file
byte-identical. The formatting options below match the content files (`players:` followed by
`- item` at the same indentation).
"""

import re
from collections.abc import Mapping
from io import StringIO
from pathlib import Path

from ruamel.yaml import YAML

from mister.catalog.application.ratings_tool import (
    ClubSeasonRatings,
    ClubSeasonRatingsUnavailableError,
    PlayerNotInSquadError,
    PlayerRatingSource,
)
from mister.catalog.infrastructure.content_schema.base import CLUB_SEASON_PATTERN
from mister.catalog.infrastructure.content_schema.issues import IssueSink
from mister.catalog.infrastructure.content_schema.ratings_bridge import (
    club_context,
    player_stats,
)
from mister.catalog.infrastructure.content_schema.reader import load_model
from mister.catalog.infrastructure.content_schema.squad import MARKET_PREFIX, SquadFile

_LINE_WIDTH = 100


def _round_trip_yaml() -> YAML:
    yaml = YAML()
    yaml.indent(mapping=2, sequence=2, offset=0)
    yaml.width = _LINE_WIDTH
    yaml.preserve_quotes = True
    return yaml


class YamlRatingSheetStore:
    """`RatingSheetStore` over a `content/` directory."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def load(self, club_season: str) -> ClubSeasonRatings:
        path = self._squad_path(club_season)
        sink = IssueSink()
        squad = load_model(self._root, path, SquadFile, sink)
        if squad is None:
            problems = "; ".join(str(issue) for issue in sink.issues)
            raise ClubSeasonRatingsUnavailableError(
                f"{club_season} is not a valid squad: {problems}"
            )
        players = tuple(
            PlayerRatingSource(
                player_id=entry.player_id,
                display_name=entry.display_name,
                stats=player_stats(entry),
                stored_rating=entry.rating,
                override_value=None
                if entry.rating_override is None
                else entry.rating_override.value,
                override_sources=(
                    0
                    if entry.rating_override is None
                    else len({str(url) for url in entry.rating_override.sources})
                ),
            )
            for entry in squad.players
        )
        return ClubSeasonRatings(club_season, club_context(squad), players)

    def save(self, club_season: str, ratings: Mapping[str, int | None]) -> None:
        path = self._squad_path(club_season)
        original = path.read_text(encoding="utf-8")
        yaml = _round_trip_yaml()
        document = yaml.load(original)
        players = {player["player_id"]: player for player in document["players"]}
        for player_id in ratings:
            if player_id not in players:
                raise PlayerNotInSquadError(club_season, player_id)
        for player_id, rating in ratings.items():
            players[player_id]["rating"] = rating
            if rating is None:
                players[player_id]["verify"] = "pending"
        rewritten = StringIO()
        yaml.dump(document, rewritten)
        if rewritten.getvalue() != original:
            path.write_text(rewritten.getvalue(), encoding="utf-8")

    def _squad_path(self, club_season: str) -> Path:
        if club_season.startswith(MARKET_PREFIX):
            raise ClubSeasonRatingsUnavailableError(
                f"{club_season} is a market squad: it has no club to compute ratings from"
            )
        path = self._root / "club-seasons" / club_season / "squad.yaml"
        if not re.fullmatch(CLUB_SEASON_PATTERN, club_season) or not path.is_file():
            raise ClubSeasonRatingsUnavailableError(
                f"{club_season} has no squad.yaml in {self._root}"
            )
        return path
