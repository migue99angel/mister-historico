"""Shared context of the per-season integrity checks."""

from dataclasses import dataclass
from datetime import date

from mister.catalog.infrastructure.content_schema.issues import IssueSink
from mister.catalog.infrastructure.content_schema.season import (
    Block,
    Competition,
    LeagueCompetition,
    Stage,
)
from mister.catalog.infrastructure.content_schema.tree import ContentTree, SeasonContent


@dataclass(frozen=True)
class SeasonContext:
    """Everything a check needs to know about one playable season, plus where to report."""

    tree: ContentTree
    failed_club_seasons: frozenset[str]
    slug: str
    sink: IssueSink

    @property
    def content(self) -> SeasonContent:
        return self.tree.seasons[self.slug]

    @property
    def own(self) -> str:
        return self.content.season.club_season

    @property
    def blocks(self) -> tuple[Block, ...]:
        return self.content.season.blocks

    @property
    def competitions(self) -> dict[str, Competition]:
        return {c.id: c for c in self.content.season.competitions}

    @property
    def leagues(self) -> dict[str, LeagueCompetition]:
        return {c.id: c for c in self.competitions.values() if isinstance(c, LeagueCompetition)}

    @property
    def own_players(self) -> set[str]:
        squad = self.tree.squads.get(self.own)
        return {p.player_id for p in squad.players} if squad else set()

    def add(self, file: str, field: str, message: str) -> None:
        self.sink.add(f"seasons/{self.slug}/{file}.yaml", field, message)

    def exists(self, club_season: str) -> bool:
        """The club-season exists, even if its file failed to load (no cascading errors)."""
        return club_season in self.tree.club_season_ids or club_season in self.failed_club_seasons

    def has_squad(self, club_season: str) -> bool:
        return club_season in self.tree.squads or club_season in self.failed_club_seasons

    def block_of(self, day: date) -> Block | None:
        return next((b for b in self.blocks if b.start <= day <= b.end), None)


def stage_of(competition: Competition, stage_id: str) -> Stage | None:
    """The stage with that id, or None (leagues have no stages)."""
    if isinstance(competition, LeagueCompetition):
        return None
    return next((s for s in competition.stages if s.id == stage_id), None)
