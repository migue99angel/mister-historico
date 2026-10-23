"""YAML adapter of `RatingSheetStore`: reads a squad file and rewrites only its ratings.

Reading uses the content schema, so the statistics are validated like anywhere else. Writing
is a targeted substitution: the YAML is composed only to find the line of each player's
`rating` (and `verify`), and just the value on that line is replaced. Every other byte of the
file (comments, indentation, line breaks, long lines) stays as it was, and a save that changes
nothing leaves the file untouched.
"""

import re
from collections.abc import Mapping
from pathlib import Path

import yaml

from mister.catalog.application.ports import (
    ClubSeasonRatings,
    ClubSeasonRatingsUnavailableError,
    PlayerNotInSquadError,
    PlayerRatingSource,
)
from mister.catalog.domain.ratings import distinct_source_count
from mister.catalog.infrastructure.content_schema.base import CLUB_SEASON_PATTERN
from mister.catalog.infrastructure.content_schema.issues import IssueSink
from mister.catalog.infrastructure.content_schema.ratings_bridge import (
    club_context,
    player_stats,
)
from mister.catalog.infrastructure.content_schema.reader import load_model
from mister.catalog.infrastructure.content_schema.squad import SquadFile

_RATING_LINE = re.compile(r"^(\s*(?:-\s+)?rating:[ \t]*)(null|~|\d+)([ \t]*(?:#.*)?\r?\n?)$")
_VERIFY_LINE = re.compile(r"^(\s*(?:-\s+)?verify:[ \t]*)(ok|pending)([ \t]*(?:#.*)?\r?\n?)$")


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
                club=club_context(entry.club_data or squad.club_data),
                stored_rating=entry.rating,
                override_value=None
                if entry.rating_override is None
                else entry.rating_override.value,
                override_sources=0
                if entry.rating_override is None
                else distinct_source_count(str(url) for url in entry.rating_override.sources),
                partial_season=entry.joined_on is not None or entry.left_on is not None,
            )
            for entry in squad.players
        )
        return ClubSeasonRatings(club_season, players)

    def save(self, club_season: str, ratings: Mapping[str, int | None]) -> None:
        path = self._squad_path(club_season)
        original = path.read_bytes().decode("utf-8")
        lines = original.splitlines(keepends=True)
        players = _player_nodes(original)
        for player_id in ratings:
            if player_id not in players:
                raise PlayerNotInSquadError(club_season, player_id)
        for player_id, rating in ratings.items():
            fields = players[player_id]
            _rewrite(
                lines, fields, "rating", _RATING_LINE, "null" if rating is None else str(rating)
            )
            if rating is None:
                _rewrite(lines, fields, "verify", _VERIFY_LINE, "pending")
        rewritten = "".join(lines)
        if rewritten != original:
            path.write_bytes(rewritten.encode("utf-8"))

    def _squad_path(self, club_season: str) -> Path:
        path = self._root / "club-seasons" / club_season / "squad.yaml"
        if not re.fullmatch(CLUB_SEASON_PATTERN, club_season) or not path.is_file():
            raise ClubSeasonRatingsUnavailableError(
                f"{club_season} has no squad.yaml in {self._root}"
            )
        return path


def _player_nodes(text: str) -> dict[str, dict[str, yaml.Node]]:
    """The key nodes of every player, by `player_id`."""
    document = yaml.compose(text, Loader=yaml.SafeLoader)
    if not isinstance(document, yaml.MappingNode):
        return {}
    for key, value in document.value:
        if key.value == "players" and isinstance(value, yaml.SequenceNode):
            return _index(value)
    return {}


def _index(players: yaml.SequenceNode) -> dict[str, dict[str, yaml.Node]]:
    found: dict[str, dict[str, yaml.Node]] = {}
    for item in players.value:
        keys = {key.value: key for key, _ in item.value}
        ids = [value.value for key, value in item.value if key.value == "player_id"]
        found[ids[0]] = keys
    return found


def _rewrite(
    lines: list[str],
    fields: Mapping[str, yaml.Node],
    name: str,
    pattern: re.Pattern[str],
    value: str,
) -> None:
    index = fields[name].start_mark.line
    match = pattern.match(lines[index])
    if match is None:
        raise ClubSeasonRatingsUnavailableError(
            f"cannot rewrite the {name} on line {index + 1}: unusual format "
            f"({lines[index].strip()!r})"
        )
    lines[index] = f"{match.group(1)}{value}{match.group(3)}"
