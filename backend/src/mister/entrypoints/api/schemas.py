"""Strict request and response models for the F3 HTTP API."""
# ruff: noqa: E501

from __future__ import annotations

from datetime import date  # noqa: TC003
from typing import Annotated, Literal
from uuid import UUID  # noqa: TC003

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StringConstraints

Slug = Annotated[
    str, StringConstraints(min_length=1, max_length=64, pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")
]


class StrictBody(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class StartRunBody(StrictBody):
    season_id: Slug = Field(alias="seasonId")


class TakeDecisionBody(StrictBody):
    expected_version: StrictInt = Field(alias="expectedVersion", ge=0)
    dilemma_id: Slug = Field(alias="dilemmaId")
    option_id: Slug = Field(alias="optionId")


class AdvanceBody(StrictBody):
    expected_version: StrictInt = Field(alias="expectedVersion", ge=0)


# Response schemas generated from contracts/openapi.yaml; regenerate with the T3.6 model generator.

ClubSeasonId = Annotated[
    str,
    StringConstraints(pattern="^(_market-)?[a-z0-9]+(-[a-z0-9]+)*$", min_length=1, max_length=64),
]
CompetitionKind = Literal["league", "cup", "super_cup", "continental_cup"]
CompetitionPriorityLevel = Literal["low", "normal", "high"]
CompetitionTier = Literal[
    "domestic_league",
    "domestic_cup",
    "domestic_super_cup",
    "continental_primary",
    "continental_secondary",
]
HexColor = Annotated[str, StringConstraints(pattern="^#[0-9a-fA-F]{6}$")]
PlayerPosition = Literal["GK", "DF", "MF", "FW"]
RunStatus = Literal["in_progress", "finished", "sacked"]
TacticStyle = Literal["pressing", "counter", "possession", "balanced"]
Venue = Literal["home", "away", "neutral"]


class BlockEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["transfer", "dressing_room", "press", "board", "milestone"] = Field(...)
    date_value: date = Field(..., alias="date")
    text: str = Field(..., description="Event text, already localised.")


class BlockProgress(BaseModel):
    model_config = ConfigDict(extra="forbid")
    number: int = Field(..., ge=1, description="One-based block number.")
    total: int = Field(..., ge=1, description="Number of blocks of the season.")
    label: str = Field(..., description="Period covered by the block, for example `August`.")


class BoardObjective(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: Slug = Field(...)
    description: str = Field(..., description="Objective text.")
    competition_id: Slug | None = Field(
        default=None,
        description="Competition the objective refers to, if any.",
        alias="competitionId",
    )


class Competition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: Slug = Field(...)
    name: str = Field(..., description="Competition name.")
    kind: Literal["league", "cup", "super_cup", "continental_cup"] = Field(...)
    tier: Literal[
        "domestic_league",
        "domestic_cup",
        "domestic_super_cup",
        "continental_primary",
        "continental_secondary",
    ] = Field(...)


class CompetitionPriority(BaseModel):
    model_config = ConfigDict(extra="forbid")
    competition_id: Slug = Field(..., alias="competitionId")
    priority: Literal["low", "normal", "high"] = Field(...)


class Decision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dilemma_id: Slug = Field(..., alias="dilemmaId")
    option_id: Slug = Field(..., alias="optionId")
    block_number: int = Field(
        ..., ge=1, description="Block in which the decision was taken.", alias="blockNumber"
    )


class DilemmaOption(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: Slug = Field(...)
    label: str = Field(..., description="Short option text.")


class ExtraTimeScore(BaseModel):
    model_config = ConfigDict(extra="forbid")
    home: int = Field(..., ge=0)
    away: int = Field(..., ge=0)


class InjuryReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    player_id: Slug = Field(..., alias="playerId")
    player_name: str = Field(..., alias="playerName")
    date_value: date = Field(..., alias="date")
    days_out: int = Field(..., ge=1, alias="daysOut")


class InjuryStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")
    days_out: int = Field(
        ..., ge=1, description="Days the player is expected to be out.", alias="daysOut"
    )


class PenaltyScore(BaseModel):
    model_config = ConfigDict(extra="forbid")
    home: int = Field(..., ge=0)
    away: int = Field(..., ge=0)


class PlayerSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: Slug = Field(...)
    display_name: str = Field(
        ..., description="Name shown according to the name policy.", alias="displayName"
    )
    position: Literal["GK", "DF", "MF", "FW"] = Field(...)
    age: int = Field(..., ge=15, le=50)
    rating: int = Field(
        ..., ge=1, le=99, description="Rating from 1 to 99 following the project rubric."
    )
    key: bool = Field(..., description="Whether this is a key player of the squad.")


class SquadMember(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: Slug = Field(...)
    display_name: str = Field(..., alias="displayName")
    position: Literal["GK", "DF", "MF", "FW"] = Field(...)
    age: int = Field(..., ge=15, le=50)
    rating: int = Field(..., ge=1, le=99)
    key: bool = Field(...)
    morale: int = Field(..., ge=0, le=100)
    fitness: int = Field(..., ge=0, le=100)
    injury: InjuryStatus | None = Field(
        ..., description="Ongoing injury, or null when the player is available."
    )


class SquadOverview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    size: int = Field(..., ge=0, description="Number of players in the squad.")
    average_rating: float = Field(..., ge=1, le=99, alias="averageRating")
    key_players: list[PlayerSummary] = Field(..., alias="keyPlayers")


class SquadStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")
    size: int = Field(..., ge=0)
    average_rating: float = Field(..., ge=1, le=99, alias="averageRating")
    players: list[SquadMember] = Field(...)


class Tactic(BaseModel):
    model_config = ConfigDict(extra="forbid")
    style: Literal["pressing", "counter", "possession", "balanced"] = Field(...)
    system: str = Field(
        ...,
        pattern="^[1-9](-[1-9]){2,4}$",
        description="Formation as 3 to 5 lines separated by hyphens, for example `4-4-2` or `4-1-2-1-2`. The regex only checks the shape; the rules that do not fit in it are that every line has between 1 and 6 players and that the lines add up to 10 (the goalkeeper is not counted).",
    )


class TeamColors(BaseModel):
    model_config = ConfigDict(extra="forbid")
    primary: HexColor = Field(...)
    secondary: HexColor = Field(...)


class TeamRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    club_season_id: ClubSeasonId = Field(..., alias="clubSeasonId")
    name: str = Field(..., description="Club name.")
    short_name: str = Field(..., description="Short club name.", alias="shortName")
    colors: TeamColors = Field(...)
    is_user: bool = Field(
        ..., description="Whether it is the team coached by the player.", alias="isUser"
    )


class TeamState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    morale: int = Field(..., ge=0, le=100, description="Dressing-room morale.")
    board_confidence: int = Field(
        ...,
        ge=0,
        le=100,
        description="Board confidence. Falling under the threshold gets the manager sacked.",
        alias="boardConfidence",
    )
    fitness: int = Field(..., ge=0, le=100, description="Average physical condition of the squad.")


class Dilemma(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: Slug = Field(...)
    title: str = Field(..., description="Short title of the dilemma.")
    prompt: str = Field(..., description="The question presented to the player.")
    options: list[DilemmaOption] = Field(..., min_length=2)


class MatchReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fixture_id: Slug = Field(..., alias="fixtureId")
    competition_id: Slug = Field(..., alias="competitionId")
    competition_name: str = Field(..., alias="competitionName")
    round: str = Field(
        default=None, description="Round or matchday label, for example `Matchday 7` or `Final`."
    )  # type: ignore[assignment]
    date_value: date = Field(..., alias="date")
    home: TeamRef = Field(...)
    away: TeamRef = Field(...)
    home_goals: int = Field(..., ge=0, description="Goals after 90 minutes.", alias="homeGoals")
    away_goals: int = Field(..., ge=0, description="Goals after 90 minutes.", alias="awayGoals")
    extra_time: ExtraTimeScore | None = Field(
        ...,
        description="Goals scored in extra time, or null when there was none.",
        alias="extraTime",
    )
    penalties: PenaltyScore | None = Field(
        ..., description="Shoot-out result, or null when there was none."
    )
    venue: Literal["home", "away", "neutral"] = Field(
        ...,
        description="`home` or `away` for the player's team, or `neutral` (for example a final). It is relative to the player's team, not to the listed home side.",
    )
    is_key_match: bool = Field(
        ...,
        description="Whether the match is highlighted (derbies, knockout ties, finals).",
        alias="isKeyMatch",
    )
    key_match_label: str | None = Field(
        ...,
        description="Why the match is key, for example `Derby`. Null when it is not.",
        alias="keyMatchLabel",
    )
    user_result: Literal["win", "draw", "loss"] = Field(
        ...,
        description="Outcome for the player's team, including extra time and penalties.",
        alias="userResult",
    )


class RunView(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: UUID = Field(..., alias="runId")
    season_id: Slug = Field(..., alias="seasonId")
    status: Literal["in_progress", "finished", "sacked"] = Field(...)
    version: int = Field(
        ..., ge=0, description="Optimistic-locking version, incremented by every command."
    )
    block: BlockProgress = Field(...)
    pending_dilemmas: list[Dilemma] = Field(
        ...,
        description="Dilemmas of the current block still to be decided.",
        alias="pendingDilemmas",
    )
    decisions: list[Decision] = Field(..., description="Decisions taken so far, oldest first.")
    state: TeamState = Field(...)
    squad: SquadStatus = Field(...)
    tactic: Tactic = Field(...)
    competition_priorities: list[CompetitionPriority] = Field(
        ...,
        description="Current priority of every competition of the season.",
        alias="competitionPriorities",
    )
    last_block_summary: BlockSummary | None = Field(
        ...,
        description="Summary of the last simulated block, or null before the first one.",
        alias="lastBlockSummary",
    )
    sacked_month: int | None = Field(
        ...,
        ge=1,
        le=12,
        description="Calendar month in which the manager was sacked, or null otherwise.",
        alias="sackedMonth",
    )


class SeasonDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: Slug = Field(...)
    club_name: str = Field(..., alias="clubName")
    short_name: str = Field(..., alias="shortName")
    season_label: str = Field(..., pattern="^[0-9]{4}-[0-9]{2}$", alias="seasonLabel")
    historical_manager: str = Field(..., alias="historicalManager")
    colors: TeamColors = Field(...)
    presentation: str = Field(
        ..., description="Presentation of the situation the manager inherits."
    )
    board_objectives: list[BoardObjective] = Field(..., alias="boardObjectives")
    squad: SquadOverview = Field(...)
    competitions: list[Competition] = Field(...)
    block_count: int = Field(
        ..., ge=1, description="Number of blocks the season is split into.", alias="blockCount"
    )


class SeasonSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: Slug = Field(...)
    club_name: str = Field(..., description="Full club name.", alias="clubName")
    short_name: str = Field(..., description="Short club name.", alias="shortName")
    season_label: str = Field(
        ...,
        pattern="^[0-9]{4}-[0-9]{2}$",
        description="Season label, for example `2000-01`.",
        alias="seasonLabel",
    )
    historical_manager: str = Field(
        ..., description="Name of the real manager of that season.", alias="historicalManager"
    )
    colors: TeamColors = Field(...)


class StandingRow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    position: int = Field(..., ge=1)
    previous_position: int | None = Field(
        default=None,
        ge=1,
        description="Position at the end of the previous block, or null in the first block.",
        alias="previousPosition",
    )
    team: TeamRef = Field(...)
    played: int = Field(..., ge=0)
    won: int = Field(..., ge=0)
    drawn: int = Field(..., ge=0)
    lost: int = Field(..., ge=0)
    goals_for: int = Field(..., ge=0, alias="goalsFor")
    goals_against: int = Field(..., ge=0, alias="goalsAgainst")
    points: int = Field(..., ge=0)


class Standings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    competition_id: Slug = Field(..., alias="competitionId")
    competition_name: str = Field(..., alias="competitionName")
    stage_id: Slug = Field(
        default=None,
        description="Stage of the competition, only for group-stage tables.",
        alias="stageId",
    )  # type: ignore[assignment]
    group_id: Slug = Field(
        default=None,
        description="Group within the stage, only for group-stage tables.",
        alias="groupId",
    )  # type: ignore[assignment]
    rows: list[StandingRow] = Field(...)


class StartRunResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_token: str = Field(
        ...,
        min_length=43,
        max_length=128,
        pattern="^[A-Za-z0-9_-]+$",
        description="Secret bearer token: opaque, server-generated, at least 32 bytes encoded URL-safe. The client stores it; it is never returned again.",
        alias="runToken",
    )
    run: RunView = Field(...)


class BlockSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    block_number: int = Field(..., ge=1, alias="blockNumber")
    label: str = Field(..., description="Period covered by the block.")
    results: list[MatchReport] = Field(...)
    standings: list[Standings] = Field(...)
    events: list[BlockEvent] = Field(...)
    injuries: list[InjuryReport] = Field(...)


class SeasonList(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[SeasonSummary] = Field(...)


class FieldError(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field: str
    message: str


class Problem(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: str = Field(json_schema_extra={"format": "uri-reference"})
    title: str
    status: int = Field(ge=400, le=599)
    code: Literal[
        "validation_error",
        "idempotency_key_required",
        "run_token_required",
        "run_token_invalid",
        "alias_already_set",
        "season_not_found",
        "run_not_found",
        "version_conflict",
        "pending_dilemmas",
        "dilemma_already_decided",
        "run_already_finished",
        "run_not_finished",
        "invalid_option",
        "idempotency_key_conflict",
        "alias_rejected",
        "rate_limited",
    ]
    detail: str = Field(default=None)  # type: ignore[assignment]
    instance: str = Field(default=None, json_schema_extra={"format": "uri-reference"})  # type: ignore[assignment]
    errors: list[FieldError] = Field(default=None)  # type: ignore[arg-type]
