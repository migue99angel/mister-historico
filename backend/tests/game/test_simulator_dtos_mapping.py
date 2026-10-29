"""The Game simulator DTOs carry the same information as the engine's published API.

`mister.simulation.application.api` (T1.6) cannot be imported from `game/application` (rules R6
and R7), and may not be on this branch yet, so the correspondence is pinned by a table: for each
engine DTO, its fields (copied from the API) and where each one lives in the Game DTO. The test
fails if a Game field is not accounted for, if a mapped field does not exist, or if an engine
field is neither mapped nor listed as completed by the adapter. The adapter of T3.5 owns the
real round-trip test against the real API.
"""

from dataclasses import fields

import pytest

from mister.game.application import ports
from mister.simulation.application import api as simulation_api


def _same(*names: str) -> dict[str, str | None]:
    return {name: name for name in names}


# engine DTO -> (Game DTO, {engine field: Game field, or None when the adapter supplies it})
CORRESPONDENCE: dict[str, tuple[type, dict[str, str | None]]] = {
    "TacticDTO": (ports.TacticSetup, _same("style", "system")),
    "SquadPlayerInput": (
        ports.SquadPlayerState,
        _same(
            "player_id",
            "position",
            "rating",
            "age",
            "morale",
            "fitness",
            "injured_until",
            "youth_minutes",
        ),
    ),
    "SquadTeamInput": (ports.TeamSquad, _same("club_season_id", "players", "tactic")),
    "ForcedInjuryDTO": (ports.ForcedInjury, _same("player_id", "date", "days")),
    "BlockSimRequest": (
        ports.BlockSimulationRequest,
        {
            "season": None,  # SeasonSimInput: completed from SeasonContentProvider
            "state_as_of": "state_as_of",
            **_same(
                "block_id",
                "start",
                "end",
                "managed_team",
                "team_morale",
                "team_overrides",
                "competition_priorities",
                "forced_injuries_from_effects",
                "prior_results",
                "squad_memberships",
                "player_pool",
                "key_starter",
            ),
        },
    ),
    "MatchResultDTO": (
        ports.MatchOutcome,
        _same(
            "fixture_id",
            "competition_id",
            "date",
            "home",
            "away",
            "regulation",
            "venue",
            "opponent",
            "user_result",
            "extra_time",
            "penalties",
            "winner",
            "key",
            "round",
            "stage_id",
            "group_id",
            "leg",
        ),
    ),
    "InjuryDTO": (ports.InjuryOutcome, _same("player_id", "date", "days", "forced")),
    "PlayerStateDTO": (
        ports.PlayerOutcome,
        _same("player_id", "fitness", "injured_until", "minutes_played"),
    ),
    "EventDTO": (
        ports.BlockEvent,
        _same("kind", "date", "club_season_id", "competition_id", "stage_id"),
    ),
    "StandingRowDTO": (
        ports.StandingRow,
        _same(
            "club_season_id",
            "position",
            "played",
            "won",
            "drawn",
            "lost",
            "goals_for",
            "goals_against",
            "points",
        ),
    ),
    "StandingsDTO": (
        ports.Standings,
        _same("competition_id", "as_of", "rows", "stage_id", "group_id", "unresolved_ties"),
    ),
    "BlockSummaryDTO": (
        ports.BlockSimulationResult,
        {
            "results": "matches",
            **_same(
                "block_id",
                "key_matches",
                "standings",
                "events",
                "injuries",
                "player_states",
                "unresolved_knockout_ties",
                "key_starter_outcome",
            ),
        },
    ),
    "KeyStarterSelection": (ports.KeyStarterSelection, _same("fixture_id", "date", "player_id")),
    "KeyStarterOutcome": (
        ports.KeyStarterOutcome,
        _same("fixture_id", "date", "player_id", "starter_ids", "absence_reason"),
    ),
    "LineupProjectionDTO": (ports.LineupProjection, _same("starter_ids", "reserve_ids")),
}

# Game fields with no engine field: the adapter uses them to build the engine call.
GAME_ONLY = {"BlockSimRequest": {"playable_season_id", "captured_content", "seed"}}


@pytest.mark.parametrize("engine_dto", sorted(CORRESPONDENCE))
def test_every_game_field_is_accounted_for_and_every_mapped_field_exists(engine_dto: str) -> None:
    game_cls, mapping = CORRESPONDENCE[engine_dto]
    game_fields = {f.name for f in fields(game_cls)}
    mapped = {target for target in mapping.values() if target is not None}

    assert mapped <= game_fields
    assert game_fields - mapped == GAME_ONLY.get(engine_dto, set())


def test_the_only_engine_field_game_does_not_hold_is_the_season_reference() -> None:
    unmapped = {
        (name, field)
        for name, (_, mapping) in CORRESPONDENCE.items()
        for field, target in mapping.items()
        if target is None
    }

    assert unmapped == {("BlockSimRequest", "season")}


def test_the_correspondence_table_covers_the_published_simulation_api() -> None:
    for engine_name, (game_cls, mapped_fields) in CORRESPONDENCE.items():
        engine_cls = getattr(simulation_api, engine_name)
        engine_fields = {field.name for field in fields(engine_cls)}
        assert set(mapped_fields) == engine_fields
        assert {target for target in mapped_fields.values() if target is not None} <= {
            field.name for field in fields(game_cls)
        }
