"""The published `Literal`s, domain enums, content schema and OpenAPI share one vocabulary."""

from enum import StrEnum
from pathlib import Path
from typing import Any, get_args

import yaml

from mister.catalog.infrastructure.content_schema import effects, fixtures, season, squad
from mister.simulation.application import api
from mister.simulation.domain.model import Position, Priority, Style, Venue

_OPENAPI = Path(__file__).parents[4] / "contracts" / "openapi.yaml"


def _values(literal: Any) -> set[str]:
    return set(get_args(literal.__value__))


def _members(enum: type[StrEnum]) -> set[str]:
    return {member.value for member in enum}


def test_api_literals_match_the_domain_enums() -> None:
    assert _values(api.PositionName) == _members(Position)
    assert _values(api.StyleName) == _members(Style)
    assert _values(api.PriorityName) == _members(Priority)
    assert _values(api.TeamVenueName) == _members(Venue)
    assert _values(api.VenueName) == _members(Venue) - {"away"}


def test_api_literals_match_the_content_schema() -> None:
    assert _values(api.PositionName) == _members(squad.Position)
    assert _values(api.StyleName) == set(get_args(effects.TacticStyle))
    assert _values(api.PriorityName) == set(get_args(effects.Priority))
    assert _values(api.TeamVenueName) == set(get_args(fixtures.Venue))
    assert _values(api.RoundName) == set(get_args(season.Round))
    assert _values(api.TiebreakerName) == _members(season.Tiebreaker)
    assert _values(api.CompetitionKindName) == {
        "league",
        "cup",
        "super_cup",
        "continental_cup",
    }
    assert _values(api.CompetitionTierName) == {
        "domestic_league",
        "domestic_cup",
        "domestic_super_cup",
        "continental_primary",
        "continental_secondary",
    }


def test_venue_matches_the_openapi_contract() -> None:
    spec = yaml.safe_load(_OPENAPI.read_text(encoding="utf-8"))

    assert set(spec["components"]["schemas"]["Venue"]["enum"]) == _values(api.TeamVenueName)
    user_results = spec["components"]["schemas"]["MatchReport"]["properties"]["userResult"]["enum"]
    assert set(user_results) == _values(api.UserResultName)
