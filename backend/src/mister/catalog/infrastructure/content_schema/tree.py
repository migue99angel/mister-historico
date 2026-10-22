"""The in-memory content tree: every validated file of a `content/` directory."""

from dataclasses import dataclass, field

from mister.catalog.infrastructure.content_schema.club import ClubFile
from mister.catalog.infrastructure.content_schema.dilemmas import DilemmasFile
from mister.catalog.infrastructure.content_schema.fixtures import FixturesFile
from mister.catalog.infrastructure.content_schema.season import SeasonFile
from mister.catalog.infrastructure.content_schema.squad import AggregateFile, SquadFile
from mister.catalog.infrastructure.content_schema.standings import StandingsFile
from mister.catalog.infrastructure.content_schema.texts import TextsFile

SEASON_FILES = ("season", "fixtures", "standings", "dilemmas", "texts")


@dataclass(frozen=True)
class SeasonContent:
    """The five files of a playable season (`content/seasons/<slug>/`)."""

    season: SeasonFile
    fixtures: FixturesFile
    standings: StandingsFile
    dilemmas: DilemmasFile
    texts: TextsFile


@dataclass(frozen=True)
class ContentTree:
    """A validated content tree. Keys are club ids, club-season slugs and season slugs.

    `squads` holds the full squads (including market squads such as `_market-2000-01`);
    `aggregates` holds the rivals that only have an aggregate strength.
    """

    clubs: dict[str, ClubFile] = field(default_factory=dict)
    squads: dict[str, SquadFile] = field(default_factory=dict)
    aggregates: dict[str, AggregateFile] = field(default_factory=dict)
    seasons: dict[str, SeasonContent] = field(default_factory=dict)

    @property
    def club_season_ids(self) -> frozenset[str]:
        return frozenset(self.squads) | frozenset(self.aggregates)
