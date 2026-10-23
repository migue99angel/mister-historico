"""Schema of clubs, squads and aggregate rivals."""

from copy import deepcopy
from datetime import date
from typing import Any

import pytest
from pydantic import ValidationError

from mister.catalog.infrastructure.content_schema.club import ClubFile
from mister.catalog.infrastructure.content_schema.squad import (
    AggregateFile,
    Position,
    SquadFile,
)

_SOURCE = "https://example.org/sources/test"


def season_stats(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "minutes_league": 2000,
        "starts_league": 20,
        "appearances_league": 25,
        "minutes_all": 2500,
        "starts_all": 28,
        "appearances_all": 32,
        "goals_all": 5,
        "assists_all": 4,
        "clean_sheets_all": None,
        "caps": 0,
        "awards": [],
        "sources": [_SOURCE],
        "verify": "ok",
    }
    data.update(overrides)
    return data


def club_data(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "club_matches_all": 42,
        "club_matches_league": 38,
        "level_tier": "C",
        "level_tier_basis": "11th of 20 in a fictional league.",
        "sources": [_SOURCE],
        "verify": "ok",
    }
    data.update(overrides)
    return data


def player(index: int, **overrides: Any) -> dict[str, Any]:
    position = "GK" if index == 0 else ("DF", "MF", "FW")[index % 3]
    data: dict[str, Any] = {
        "player_id": f"tfc-{index:02d}",
        "display_name": f"Fake Player {index}",
        "alias_name": f"Alias {index}",
        "position": position,
        "age": 25,
        "rating": 60,
        "key": False,
        "season_stats": season_stats(clean_sheets_all=5 if index == 0 else None),
        "sources": [_SOURCE],
        "verify": "ok",
    }
    data.update(overrides)
    return data


def squad(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "schema_version": 1,
        "club_season": "test-fc-2000-01",
        "club": "test-fc",
        "season": "2000-01",
        "real_league": {
            "competition_label": "Liga Test",
            "played": 10,
            "goals_for": 20,
            "goals_against": 12,
            "sources": [_SOURCE],
            "verify": "ok",
        },
        "club_data": club_data(),
        "sources": [_SOURCE],
        "verify": "ok",
        "players": [player(i) for i in range(18)],
    }
    data.update(overrides)
    return data


def with_player(index: int, **overrides: Any) -> dict[str, Any]:
    data = deepcopy(squad())
    data["players"][index].update(overrides)
    return data


def test_a_valid_squad_parses() -> None:
    parsed = SquadFile.model_validate(squad())

    assert parsed.players[0].position is Position.GK
    assert len(parsed.players) == 18


def test_a_rating_of_100_is_rejected() -> None:
    with pytest.raises(ValidationError, match=r"players\.3\.rating"):
        SquadFile.model_validate(with_player(3, rating=100))


def test_a_rating_of_0_is_rejected() -> None:
    with pytest.raises(ValidationError, match=r"players\.3\.rating"):
        SquadFile.model_validate(with_player(3, rating=0))


def test_a_player_without_sources_is_rejected() -> None:
    with pytest.raises(ValidationError, match="at least one source"):
        SquadFile.model_validate(with_player(3, sources=[]))


def test_a_player_source_must_be_an_http_url() -> None:
    with pytest.raises(ValidationError, match=r"players\.3\.sources"):
        SquadFile.model_validate(with_player(3, sources=["not a url"]))


def test_the_old_rating_rationale_field_is_gone() -> None:
    with pytest.raises(ValidationError, match="extra_forbidden"):
        SquadFile.model_validate(with_player(3, key=True, rating_rationale="Fine."))


def test_an_unknown_position_is_rejected() -> None:
    with pytest.raises(ValidationError, match="position"):
        SquadFile.model_validate(with_player(3, position="WINGER"))


def test_a_subrole_must_match_the_position() -> None:
    with pytest.raises(ValidationError, match="subrole"):
        SquadFile.model_validate(with_player(1, position="DF", subrole="ST"))


def test_a_matching_subrole_is_accepted() -> None:
    parsed = SquadFile.model_validate(with_player(1, position="DF", subrole="CB"))

    assert parsed.players[1].subrole is not None


def test_an_unknown_field_is_rejected() -> None:
    with pytest.raises(ValidationError, match="extra_forbidden"):
        SquadFile.model_validate(with_player(3, nickname="Foo"))


def test_a_pending_age_must_be_null_and_a_null_age_must_be_pending() -> None:
    with pytest.raises(ValidationError, match="age is null"):
        SquadFile.model_validate(with_player(3, age=None))

    parsed = SquadFile.model_validate(with_player(3, age=None, verify="pending"))

    assert parsed.players[3].age is None


def test_joined_and_left_dates_are_optional_and_ordered() -> None:
    parsed = SquadFile.model_validate(
        with_player(3, joined_on=date(2000, 9, 1), left_on=date(2001, 1, 10))
    )
    assert parsed.players[3].joined_on == date(2000, 9, 1)

    with pytest.raises(ValidationError, match="left_on"):
        SquadFile.model_validate(
            with_player(3, joined_on=date(2001, 1, 10), left_on=date(2000, 9, 1))
        )


def test_joined_date_outside_the_season_window_is_rejected() -> None:
    with pytest.raises(ValidationError, match="season window"):
        SquadFile.model_validate(with_player(3, joined_on=date(2001, 7, 1)))


def test_duplicate_player_ids_in_a_squad_are_rejected() -> None:
    data = squad()
    data["players"][5]["player_id"] = data["players"][4]["player_id"]

    with pytest.raises(ValidationError, match="duplicate player_id"):
        SquadFile.model_validate(data)


def test_a_squad_id_must_be_club_and_season() -> None:
    with pytest.raises(ValidationError, match="club_season"):
        SquadFile.model_validate(squad(club_season="other-fc-2000-01"))


def test_the_season_label_must_be_consecutive_years() -> None:
    with pytest.raises(ValidationError, match="season"):
        SquadFile.model_validate(squad(season="2000-05", club_season="test-fc-2000-05"))


def test_a_market_squad_has_no_club_and_any_size() -> None:
    parsed = SquadFile.model_validate(
        squad(
            club_season="_market-2000-01",
            club=None,
            real_league=None,
            club_data=None,
            players=[player(0, club_data=club_data(club_name="Fictional Origin FC"))],
        )
    )

    assert parsed.is_market


def test_a_non_market_squad_needs_a_club() -> None:
    with pytest.raises(ValidationError, match="club"):
        SquadFile.model_validate(squad(club=None))


def aggregate(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "schema_version": 1,
        "club_season": "agg-town-2000-01",
        "club": "agg-town",
        "season": "2000-01",
        "attack": 40,
        "defense": 38,
        "rating_rationale": "Lower-league side, rated from its league position.",
        "sources": [_SOURCE],
        "verify": "ok",
    }
    data.update(overrides)
    return data


def test_a_valid_aggregate_parses() -> None:
    assert AggregateFile.model_validate(aggregate()).attack == 40


@pytest.mark.parametrize("field", ["attack", "defense"])
def test_aggregate_strength_must_be_within_1_and_99(field: str) -> None:
    with pytest.raises(ValidationError, match=field):
        AggregateFile.model_validate(aggregate(**{field: 100}))


def test_an_aggregate_without_sources_is_rejected() -> None:
    with pytest.raises(ValidationError, match="at least one source"):
        AggregateFile.model_validate(aggregate(sources=[]))


def club(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "schema_version": 1,
        "club_id": "test-fc",
        "name": "Test FC",
        "short_name": "TFC",
        "colors": {"primary": "#112233", "secondary": "#FFFFFF"},
    }
    data.update(overrides)
    return data


def test_a_valid_club_parses() -> None:
    assert ClubFile.model_validate(club()).colors.primary == "#112233"


def test_a_club_color_must_be_a_hex_code() -> None:
    with pytest.raises(ValidationError, match=r"colors\.primary"):
        ClubFile.model_validate(club(colors={"primary": "red", "secondary": "#FFFFFF"}))


def test_a_club_squad_needs_real_league_data() -> None:
    with pytest.raises(ValidationError, match="real_league"):
        SquadFile.model_validate(squad(real_league=None))


def test_a_pending_real_league_may_be_null() -> None:
    league: dict[str, Any] = {
        "competition_label": "Liga Test",
        "played": None,
        "goals_for": None,
        "goals_against": None,
        "sources": [],
        "verify": "pending",
    }

    assert SquadFile.model_validate(squad(real_league=league)).real_league is not None


def test_a_verified_real_league_cannot_have_null_goals() -> None:
    league: dict[str, Any] = squad()["real_league"]
    league["goals_for"] = None

    with pytest.raises(ValidationError, match="goals_for is null"):
        SquadFile.model_validate(squad(real_league=league))


def test_the_old_real_goals_fields_are_gone() -> None:
    with pytest.raises(ValidationError, match="extra_forbidden"):
        SquadFile.model_validate(squad(real_goals_for=10))


def test_a_pending_rating_is_null_and_a_null_rating_is_pending() -> None:
    with pytest.raises(ValidationError, match="rating is null"):
        SquadFile.model_validate(with_player(3, rating=None))

    parsed = SquadFile.model_validate(with_player(3, rating=None, verify="pending"))

    assert parsed.players[3].rating is None


@pytest.mark.parametrize("age", [14, 51])
def test_an_age_outside_15_to_50_is_rejected(age: int) -> None:
    with pytest.raises(ValidationError, match=r"players\.3\.age"):
        SquadFile.model_validate(with_player(3, age=age))


def test_an_age_of_15_is_accepted() -> None:
    assert SquadFile.model_validate(with_player(3, age=15)).players[3].age == 15


def test_a_string_rating_is_rejected_in_strict_mode() -> None:
    with pytest.raises(ValidationError, match=r"players\.3\.rating"):
        SquadFile.model_validate(with_player(3, rating="80"))


def test_a_string_for_a_boolean_is_rejected_in_strict_mode() -> None:
    with pytest.raises(ValidationError, match=r"players\.3\.key"):
        SquadFile.model_validate(with_player(3, key="true"))


def test_a_default_tactic_is_optional_and_balanced_442_by_default() -> None:
    assert SquadFile.model_validate(squad()).default_tactic.system == "4-4-2"
    assert SquadFile.model_validate(squad()).default_tactic.style == "balanced"

    parsed = SquadFile.model_validate(squad(default_tactic={"style": "counter", "system": "5-3-2"}))
    assert parsed.default_tactic.style == "counter"


def test_a_pending_aggregate_strength_may_be_null() -> None:
    parsed = AggregateFile.model_validate(
        aggregate(attack=None, defense=None, rating_rationale=None, verify="pending")
    )

    assert parsed.attack is None


def test_a_verified_aggregate_needs_a_rationale() -> None:
    with pytest.raises(ValidationError, match="rating_rationale"):
        AggregateFile.model_validate(aggregate(rating_rationale=None))


def test_a_club_season_slug_has_at_most_64_characters() -> None:
    ok_club = "a" * 56  # 56 + "-2000-01" = 64
    ok = squad(club_season=f"{ok_club}-2000-01", club=ok_club)
    assert SquadFile.model_validate(ok)

    long_club = "a" * 57  # 65 characters
    with pytest.raises(ValidationError, match="club_season"):
        SquadFile.model_validate(squad(club_season=f"{long_club}-2000-01", club=long_club))


# ------------------------------------------------------------------ season stats and overrides
def test_season_stats_are_parsed_with_their_awards() -> None:
    awards = [{"name": "Top scorer", "tier": "L", "source": _SOURCE}]

    parsed = SquadFile.model_validate(with_player(3, season_stats=season_stats(awards=awards)))

    stats = parsed.players[3].season_stats
    assert stats is not None
    assert stats.awards is not None
    assert stats.awards[0].tier == "L"


def test_a_club_player_without_season_stats_is_rejected() -> None:
    with pytest.raises(ValidationError, match=r"players\.3\.season_stats"):
        SquadFile.model_validate(with_player(3, season_stats=None))


def test_a_club_squad_without_club_data_is_rejected() -> None:
    with pytest.raises(ValidationError, match="club_data"):
        SquadFile.model_validate(squad(club_data=None))


MARKET = {"club_season": "_market-2000-01", "club": None, "real_league": None}


def market_player(index: int = 0, **overrides: Any) -> dict[str, Any]:
    data = {"club_data": club_data(club_name="Fictional Origin FC")}
    data.update(overrides)
    return player(index, **data)


def test_a_market_player_carries_stats_and_the_data_of_his_own_club() -> None:
    parsed = SquadFile.model_validate(squad(**MARKET, club_data=None, players=[market_player(1)]))

    entry = parsed.players[0]
    assert entry.season_stats is not None
    assert entry.club_data is not None
    assert entry.club_data.club_name == "Fictional Origin FC"


def test_a_market_player_needs_his_club_data_with_the_club_name() -> None:
    without = player(1)
    with pytest.raises(ValidationError, match=r"players\.0\.club_data is required"):
        SquadFile.model_validate(squad(**MARKET, club_data=None, players=[without]))
    nameless = market_player(1, club_data=club_data())
    with pytest.raises(ValidationError, match=r"players\.0\.club_data\.club_name"):
        SquadFile.model_validate(squad(**MARKET, club_data=None, players=[nameless]))


def test_a_market_squad_has_no_squad_level_club_data() -> None:
    with pytest.raises(ValidationError, match="a market squad has no club_data"):
        SquadFile.model_validate(squad(**MARKET, players=[market_player(1)]))


def test_a_club_squad_player_cannot_carry_his_own_club_data() -> None:
    with pytest.raises(ValidationError, match=r"players\.3\.club_data"):
        SquadFile.model_validate(with_player(3, club_data=club_data(club_name="Other FC")))


@pytest.mark.parametrize(
    "field", ["minutes_league", "appearances_league", "goals_all", "caps", "awards"]
)
def test_a_required_statistic_may_be_null_only_while_pending(field: str) -> None:
    with pytest.raises(ValidationError, match=f"{field} is null"):
        SquadFile.model_validate(with_player(3, season_stats=season_stats(**{field: None})))

    pending = season_stats(**{field: None}, verify="pending")
    assert SquadFile.model_validate(with_player(3, season_stats=pending))


@pytest.mark.parametrize(
    "field",
    ["starts_league", "minutes_all", "starts_all", "appearances_all", "assists_all"],
)
def test_an_optional_statistic_may_be_null_when_verified(field: str) -> None:
    parsed = SquadFile.model_validate(with_player(3, season_stats=season_stats(**{field: None})))

    assert parsed.players[3].season_stats is not None


def test_a_goalkeeper_may_leave_clean_sheets_null() -> None:
    assert SquadFile.model_validate(
        with_player(0, season_stats=season_stats(clean_sheets_all=None))
    )


def test_clean_sheets_of_an_outfield_player_are_rejected() -> None:
    with pytest.raises(ValidationError, match="clean_sheets_all is only for goalkeepers"):
        SquadFile.model_validate(with_player(1, season_stats=season_stats(clean_sheets_all=3)))


@pytest.mark.parametrize(
    "field", ["minutes_league", "starts_all", "goals_all", "assists_all", "caps"]
)
def test_a_negative_statistic_is_rejected(field: str) -> None:
    with pytest.raises(ValidationError, match=field):
        SquadFile.model_validate(with_player(3, season_stats=season_stats(**{field: -1})))


def test_available_matches_must_be_positive() -> None:
    with pytest.raises(ValidationError, match="available_matches_all"):
        SquadFile.model_validate(with_player(3, season_stats=season_stats(available_matches_all=0)))


def test_starts_cannot_exceed_appearances() -> None:
    with pytest.raises(ValidationError, match="starts_all cannot exceed appearances_all"):
        SquadFile.model_validate(
            with_player(3, season_stats=season_stats(starts_all=33, appearances_all=32))
        )


def test_league_figures_cannot_exceed_the_all_competitions_figures() -> None:
    with pytest.raises(ValidationError, match="minutes_league cannot exceed minutes_all"):
        SquadFile.model_validate(
            with_player(3, season_stats=season_stats(minutes_league=2600, minutes_all=2500))
        )


@pytest.mark.parametrize(
    "award",
    [
        {"name": "Best", "tier": "X", "source": _SOURCE},
        {"name": "  ", "tier": "W", "source": _SOURCE},
        {"name": "Best", "tier": "W", "source": "nope"},
    ],
)
def test_an_award_needs_a_known_tier_a_name_and_a_url(award: dict[str, Any]) -> None:
    with pytest.raises(ValidationError, match="awards"):
        SquadFile.model_validate(with_player(3, season_stats=season_stats(awards=[award])))


def test_both_minutes_missing_means_the_statistics_are_pending() -> None:
    both = season_stats(minutes_league=None, minutes_all=None, verify="pending")

    assert SquadFile.model_validate(with_player(3, season_stats=both))


def test_a_null_position_is_allowed_only_while_pending() -> None:
    with pytest.raises(ValidationError, match="position is null"):
        SquadFile.model_validate(with_player(3, position=None))

    assert SquadFile.model_validate(with_player(3, position=None, rating=None, verify="pending"))


def override(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "value": 70,
        "rationale": "Fictional injury of 25 matches, documented in the sources.",
        "sources": [_SOURCE],
    }
    data.update(overrides)
    return data


def test_a_rating_override_with_rationale_and_sources_is_accepted() -> None:
    parsed = SquadFile.model_validate(with_player(3, key=True, rating_override=override()))

    assert parsed.players[3].rating_override is not None
    assert parsed.players[3].rating_override.value == 70


@pytest.mark.parametrize(
    "bad",
    [
        {"rationale": ""},
        {"rationale": "   "},
        {"sources": []},
        {"value": 100},
        {"value": 0},
    ],
)
def test_a_rating_override_needs_a_rationale_sources_and_a_valid_value(
    bad: dict[str, Any],
) -> None:
    with pytest.raises(ValidationError, match="rating_override"):
        SquadFile.model_validate(with_player(3, key=True, rating_override=override(**bad)))


def test_a_rating_override_without_a_rationale_is_rejected() -> None:
    data = override()
    del data["rationale"]

    with pytest.raises(ValidationError, match=r"rating_override\.rationale"):
        SquadFile.model_validate(with_player(3, rating_override=data))


def test_club_data_is_parsed() -> None:
    parsed = SquadFile.model_validate(squad())

    assert parsed.club_data is not None
    assert parsed.club_data.club_matches_all == 42
    assert parsed.club_data.level_tier == "C"


@pytest.mark.parametrize("field", ["club_matches_all", "club_matches_league", "level_tier"])
def test_club_data_may_be_null_only_while_pending(field: str) -> None:
    with pytest.raises(ValidationError, match=f"{field} is null"):
        SquadFile.model_validate(squad(club_data=club_data(**{field: None})))

    assert SquadFile.model_validate(
        squad(club_data=club_data(**{field: None}, level_tier_basis=None, verify="pending"))
    )


def test_a_verified_level_tier_needs_its_criterion() -> None:
    with pytest.raises(ValidationError, match="level_tier_basis is required"):
        SquadFile.model_validate(squad(club_data=club_data(level_tier_basis=None)))


def test_an_unknown_level_tier_is_rejected() -> None:
    with pytest.raises(ValidationError, match="level_tier"):
        SquadFile.model_validate(squad(club_data=club_data(level_tier="E")))


def test_club_data_needs_sources_when_verified() -> None:
    with pytest.raises(ValidationError, match="at least one source"):
        SquadFile.model_validate(squad(club_data=club_data(sources=[])))


def test_league_matches_cannot_exceed_all_matches() -> None:
    with pytest.raises(ValidationError, match="club_matches_league cannot exceed club_matches_all"):
        SquadFile.model_validate(
            squad(club_data=club_data(club_matches_all=30, club_matches_league=38))
        )


# ------------------------------------------------------------ coherence of the statistics
@pytest.mark.parametrize(
    ("stats", "message"),
    [
        ({"available_matches_all": 43}, "available_matches_all cannot exceed club_matches_all"),
        ({"appearances_all": 43}, "appearances_all cannot exceed the matches"),
        (
            {
                "available_matches_all": 10,
                "appearances_all": 11,
                "starts_all": 5,
                "appearances_league": 5,
                "starts_league": 2,
                "minutes_league": 400,
                "minutes_all": 900,
            },
            "appearances_all cannot exceed the matches",
        ),
        (
            {"appearances_league": 39, "appearances_all": 40},
            "appearances_league cannot exceed club_matches_league",
        ),
        ({"minutes_all": 5000}, "minutes_all cannot exceed 120 per appearance"),
        (
            {"minutes_league": 3100, "minutes_all": 4000, "appearances_all": 40},
            "minutes_league cannot exceed 120 per appearance",
        ),
        ({"goals_all": 200}, "goals_all cannot exceed 4 per appearance"),
        ({"assists_all": 200}, "assists_all cannot exceed 4 per appearance"),
    ],
)
def test_statistics_that_cannot_be_true_are_rejected(stats: dict[str, Any], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        SquadFile.model_validate(with_player(3, season_stats=season_stats(**stats)))


def test_clean_sheets_cannot_exceed_the_appearances() -> None:
    with pytest.raises(ValidationError, match="clean_sheets_all cannot exceed appearances_all"):
        SquadFile.model_validate(with_player(0, season_stats=season_stats(clean_sheets_all=33)))


def test_extra_time_leaves_room_for_120_minutes_per_appearance() -> None:
    ok = season_stats(minutes_all=3840, appearances_all=32, minutes_league=2000)

    assert SquadFile.model_validate(with_player(3, season_stats=ok))
