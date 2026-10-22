"""The closed effect DSL of dilemma options.

Effects are a discriminated union on `type`. Adding a type is a schema change (a contract
change request); content can never invent one. Delta ranges are deliberately small so no
single dilemma can swing a whole season:

| Effect | Range |
|---|---|
| `morale` (whole squad, 0-100 scale) | -20..20 |
| `player_morale` | -30..30 |
| `board_confidence` (0-100 scale) | -25..25 |
| `fitness` (whole squad or one player, 0-100 scale) | -30..30 |
| `injury` duration in days | 1..365 |
"""

from datetime import date
from typing import Annotated, Literal

from pydantic import AfterValidator, Field

from mister.catalog.infrastructure.content_schema.base import (
    ClubSeasonSlug,
    ContentModel,
    PlayerId,
    Slug,
)

MORALE_DELTA_LIMIT = 20
PLAYER_MORALE_DELTA_LIMIT = 30
BOARD_CONFIDENCE_DELTA_LIMIT = 25
FITNESS_DELTA_LIMIT = 30
MAX_INJURY_DAYS = 365

TacticStyle = Literal["pressing", "counter", "possession", "balanced"]
Priority = Literal["low", "normal", "high"]
OUTFIELD_PLAYERS = 10
MIN_LINES = 3
MAX_LINES = 5
MAX_LINE_SIZE = 6


def _check_system(value: str) -> str:
    lines = [int(part) for part in value.split("-")]
    if not MIN_LINES <= len(lines) <= MAX_LINES:
        raise ValueError(f"a system has between {MIN_LINES} and {MAX_LINES} lines")
    if any(not 1 <= line <= MAX_LINE_SIZE for line in lines):
        raise ValueError(f"every line has between 1 and {MAX_LINE_SIZE} players")
    if sum(lines) != OUTFIELD_PLAYERS:
        raise ValueError(f"a system must add up to {OUTFIELD_PLAYERS} outfield players")
    return value


System = Annotated[
    str,
    Field(pattern=r"^[1-9](-[1-9]){2,4}$", description="e.g. 4-3-3"),
    AfterValidator(_check_system),
]
"""Formation as lines of outfield players, e.g. `4-3-3` (10 players, 3 to 5 lines)."""


class Tactic(ContentModel):
    """A playing style plus a system."""

    style: TacticStyle
    system: System


class MoraleEffect(ContentModel):
    """Changes the morale of the whole squad."""

    type: Literal["morale"]
    delta: Annotated[int, Field(ge=-MORALE_DELTA_LIMIT, le=MORALE_DELTA_LIMIT)]


class PlayerMoraleEffect(ContentModel):
    """Changes the morale of one player."""

    type: Literal["player_morale"]
    player_id: PlayerId
    delta: Annotated[int, Field(ge=-PLAYER_MORALE_DELTA_LIMIT, le=PLAYER_MORALE_DELTA_LIMIT)]


class SignPlayerEffect(ContentModel):
    """Adds a player to the manager's squad.

    With `from_club_season`, the player leaves that rival's squad (he must be in it).
    Without it, he comes from the market or from outside the game.
    """

    type: Literal["sign_player"]
    player_id: PlayerId
    from_club_season: ClubSeasonSlug | None = None


class SellPlayerEffect(ContentModel):
    """Removes a player from the manager's squad, optionally into a rival's squad."""

    type: Literal["sell_player"]
    player_id: PlayerId
    to_club_season: ClubSeasonSlug | None = None


class SetTacticEffect(ContentModel):
    """Sets the team's playing style and system."""

    type: Literal["set_tactic"]
    style: TacticStyle
    system: System


class CompetitionPriorityEffect(ContentModel):
    """Sets how much the manager rotates in a competition versus the others."""

    type: Literal["competition_priority"]
    competition_id: Slug
    priority: Priority


class BoardConfidenceEffect(ContentModel):
    """Changes the board's confidence in the manager."""

    type: Literal["board_confidence"]
    delta: Annotated[int, Field(ge=-BOARD_CONFIDENCE_DELTA_LIMIT, le=BOARD_CONFIDENCE_DELTA_LIMIT)]


class YouthMinutesEffect(ContentModel):
    """Gives minutes to a young player."""

    type: Literal["youth_minutes"]
    player_id: PlayerId


class InjuryEffect(ContentModel):
    """A forced injury: the player is out from `date` for `days` days."""

    type: Literal["injury"]
    player_id: PlayerId
    date: date
    days: Annotated[int, Field(ge=1, le=MAX_INJURY_DAYS)]


class FitnessEffect(ContentModel):
    """Changes the fitness of the whole squad, or of one player when `player_id` is set."""

    type: Literal["fitness"]
    delta: Annotated[int, Field(ge=-FITNESS_DELTA_LIMIT, le=FITNESS_DELTA_LIMIT)]
    player_id: PlayerId | None = None


Effect = Annotated[
    MoraleEffect
    | PlayerMoraleEffect
    | SignPlayerEffect
    | SellPlayerEffect
    | SetTacticEffect
    | CompetitionPriorityEffect
    | BoardConfidenceEffect
    | YouthMinutesEffect
    | InjuryEffect
    | FitnessEffect,
    Field(discriminator="type"),
]
