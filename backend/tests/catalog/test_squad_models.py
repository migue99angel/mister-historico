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
        "real_goals_for": 20,
        "real_goals_against": 12,
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
    with pytest.raises(ValidationError, match="players.3.sources"):
        SquadFile.model_validate(with_player(3, sources=["not a url"]))


def test_a_key_player_without_rating_rationale_is_rejected() -> None:
    with pytest.raises(ValidationError, match="rating_rationale"):
        SquadFile.model_validate(with_player(3, key=True))


def test_a_key_player_with_rating_rationale_is_accepted() -> None:
    parsed = SquadFile.model_validate(with_player(3, key=True, rating_rationale="Top scorer."))

    assert parsed.players[3].key


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


def test_a_squad_needs_a_goalkeeper() -> None:
    data = squad()
    data["players"][0]["position"] = "DF"

    with pytest.raises(ValidationError, match="goalkeeper"):
        SquadFile.model_validate(data)


def test_a_club_squad_needs_at_least_18_players() -> None:
    with pytest.raises(ValidationError, match="between 18 and 40"):
        SquadFile.model_validate(squad(players=[player(i) for i in range(17)]))


def test_real_league_goals_are_null_only_when_pending() -> None:
    with pytest.raises(ValidationError, match="real_goals_for"):
        SquadFile.model_validate(squad(real_goals_for=None))

    parsed = SquadFile.model_validate(squad(real_goals_for=None, verify="pending"))

    assert parsed.real_goals_for is None


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
            real_goals_for=None,
            real_goals_against=None,
            players=[player(0)],
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
    with pytest.raises(ValidationError, match="colors.primary"):
        ClubFile.model_validate(club(colors={"primary": "red", "secondary": "#FFFFFF"}))
