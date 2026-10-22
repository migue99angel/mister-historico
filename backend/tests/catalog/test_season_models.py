"""Schema of the playable-season files: season, fixtures, standings, dilemmas and texts."""

from copy import deepcopy
from datetime import date
from typing import Any

import pytest
from pydantic import ValidationError

from mister.catalog.infrastructure.content_schema.dilemmas import DilemmasFile
from mister.catalog.infrastructure.content_schema.fixtures import FixturesFile
from mister.catalog.infrastructure.content_schema.season import SeasonFile
from mister.catalog.infrastructure.content_schema.standings import StandingsFile
from mister.catalog.infrastructure.content_schema.texts import TextsFile

_SRC = ["https://example.org/sources/test"]
_OWN = "test-fc-2000-01"
_RIVAL = "rival-fc-2000-01"


def _blocks(count: int = 5) -> list[dict[str, Any]]:
    starts = [(8, 1), (10, 1), (12, 1), (2, 1), (4, 1), (6, 1)]
    ends = [(9, 30), (11, 30), (1, 31), (3, 31), (5, 31), (6, 30)]
    years = [2000, 2000, 2000, 2001, 2001, 2001]
    out = []
    for i in range(count):
        out.append(
            {
                "id": f"b{i + 1}",
                "label": f"Block {i + 1}",
                "start": date(years[i], *starts[i]),
                "end": date(years[i] + (1 if i == 2 else 0), *ends[i]),
            }
        )
    return out


def season(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "schema_version": 1,
        "slug": _OWN,
        "club_season": _OWN,
        "season": "2000-01",
        "manager": {
            "display_name": "Fake Manager",
            "alias_name": "The Boss",
            "sources": _SRC,
            "verify": "ok",
        },
        "blocks": _blocks(),
        "competitions": [
            {
                "kind": "league",
                "id": "liga",
                "name": "Liga Test",
                "participants": [_OWN, _RIVAL],
                "rounds": 2,
                "points_per_win": 3,
                "points_per_draw": 1,
                "tiebreakers": ["goal_difference", "goals_for"],
            },
            {
                "kind": "cup",
                "id": "copa",
                "name": "Copa Test",
                "participants": [_OWN, _RIVAL],
                "stages": [
                    {
                        "id": "semi",
                        "name": "Semi",
                        "legs": 2,
                        "away_goals_rule": True,
                        "extra_time": False,
                        "penalties": True,
                    },
                    {
                        "id": "final",
                        "name": "Final",
                        "legs": 1,
                        "away_goals_rule": False,
                        "extra_time": True,
                        "penalties": True,
                    },
                ],
            },
        ],
        "board_objectives": [
            {"competition": "liga", "kind": "finish_top", "target_position": 2, "text": "Top 2."}
        ],
        "historical_outcome": [
            {
                "competition": "liga",
                "champion": False,
                "final_position": 2,
                "eliminated_in": None,
                "sources": _SRC,
                "verify": "ok",
            },
            {
                "competition": "copa",
                "champion": False,
                "final_position": None,
                "eliminated_in": "final",
                "sources": _SRC,
                "verify": "ok",
            },
        ],
    }
    data.update(overrides)
    return data


def test_a_valid_season_parses() -> None:
    parsed = SeasonFile.model_validate(season())

    assert [c.kind for c in parsed.competitions] == ["league", "cup"]


@pytest.mark.parametrize("count", [4, 7])
def test_a_season_needs_five_or_six_blocks(count: int) -> None:
    blocks = _blocks(6)
    blocks = blocks[:count] if count < 6 else blocks + blocks[:1]
    with pytest.raises(ValidationError, match="5 or 6 blocks"):
        SeasonFile.model_validate(season(blocks=blocks))


def test_overlapping_blocks_are_rejected() -> None:
    blocks = _blocks()
    blocks[1]["start"] = date(2000, 9, 15)

    with pytest.raises(ValidationError, match="overlap"):
        SeasonFile.model_validate(season(blocks=blocks))


def test_a_block_ending_before_it_starts_is_rejected() -> None:
    blocks = _blocks()
    blocks[0]["end"] = date(2000, 7, 1)

    with pytest.raises(ValidationError, match="end"):
        SeasonFile.model_validate(season(blocks=blocks))


def test_duplicate_block_ids_are_rejected() -> None:
    blocks = _blocks()
    blocks[1]["id"] = "b1"

    with pytest.raises(ValidationError, match="duplicate block id"):
        SeasonFile.model_validate(season(blocks=blocks))


def test_an_unknown_competition_kind_is_rejected() -> None:
    data = season()
    data["competitions"][0]["kind"] = "friendly"

    with pytest.raises(ValidationError, match="union_tag_invalid"):
        SeasonFile.model_validate(data)


def test_all_four_competition_kinds_are_accepted() -> None:
    data = season()
    stage = {
        "id": "final",
        "name": "Final",
        "legs": 1,
        "away_goals_rule": False,
        "extra_time": True,
        "penalties": True,
    }
    data["competitions"] += [
        {
            "kind": "super_cup",
            "id": "supercopa",
            "name": "Supercopa",
            "participants": [_OWN, _RIVAL],
            "stages": [stage],
        },
        {
            "kind": "continental_cup",
            "id": "europa",
            "name": "Copa Continental",
            "participants": [_OWN, _RIVAL],
            "group_stage": {
                "groups": [{"id": "a", "participants": [_OWN, _RIVAL]}],
                "legs": 2,
                "points_per_win": 3,
                "tiebreakers": ["head_to_head_points", "goal_difference"],
                "advance_per_group": 1,
            },
            "stages": [stage],
        },
    ]
    data["historical_outcome"] += [
        {
            "competition": c,
            "champion": True,
            "final_position": None,
            "eliminated_in": None,
            "sources": _SRC,
            "verify": "ok",
        }
        for c in ("supercopa", "europa")
    ]

    assert len(SeasonFile.model_validate(data).competitions) == 4


def test_away_goals_rule_needs_a_two_legged_stage() -> None:
    data = season()
    data["competitions"][1]["stages"][1]["away_goals_rule"] = True

    with pytest.raises(ValidationError, match="away_goals_rule"):
        SeasonFile.model_validate(data)


def test_a_league_needs_a_known_number_of_rounds() -> None:
    data = season()
    data["competitions"][0]["rounds"] = 3

    with pytest.raises(ValidationError, match="rounds"):
        SeasonFile.model_validate(data)


def test_an_unknown_tiebreaker_is_rejected() -> None:
    data = season()
    data["competitions"][0]["tiebreakers"] = ["coin_toss"]

    with pytest.raises(ValidationError, match="tiebreakers"):
        SeasonFile.model_validate(data)


def test_the_own_club_season_must_take_part_in_every_competition() -> None:
    data = season()
    data["competitions"][1]["participants"] = [_RIVAL, "other-fc-2000-01"]

    with pytest.raises(ValidationError, match="participants"):
        SeasonFile.model_validate(data)


def test_duplicate_competition_ids_are_rejected() -> None:
    data = season()
    data["competitions"][1]["id"] = "liga"

    with pytest.raises(ValidationError, match="duplicate competition id"):
        SeasonFile.model_validate(data)


def test_an_objective_pointing_to_a_missing_stage_is_rejected() -> None:
    data = season(
        board_objectives=[
            {"competition": "copa", "kind": "reach_stage", "target_stage": "nope", "text": "x"}
        ]
    )

    with pytest.raises(ValidationError, match="target_stage"):
        SeasonFile.model_validate(data)


def test_a_finish_top_objective_needs_a_target_position() -> None:
    data = season(board_objectives=[{"competition": "liga", "kind": "finish_top", "text": "x"}])

    with pytest.raises(ValidationError, match="target_position"):
        SeasonFile.model_validate(data)


def test_a_historical_outcome_without_sources_is_rejected() -> None:
    data = season()
    data["historical_outcome"][0]["sources"] = []

    with pytest.raises(ValidationError, match="at least one source"):
        SeasonFile.model_validate(data)


def test_an_outcome_cannot_be_champion_and_eliminated() -> None:
    data = season()
    data["historical_outcome"][1]["champion"] = True

    with pytest.raises(ValidationError, match="champion"):
        SeasonFile.model_validate(data)


# --------------------------------------------------------------------------- fixtures
def fixture(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": "f01",
        "date": date(2000, 9, 2),
        "competition": "liga",
        "round": 1,
        "opponent": _RIVAL,
        "venue": "home",
        "result": {"goals_for": 2, "goals_against": 1},
        "sources": _SRC,
        "verify": "ok",
    }
    data.update(overrides)
    return data


def fixtures_file(*items: dict[str, Any]) -> dict[str, Any]:
    return {"schema_version": 1, "fixtures": list(items) or [fixture()]}


def test_a_valid_fixture_parses() -> None:
    parsed = FixturesFile.model_validate(fixtures_file())

    assert parsed.fixtures[0].date == date(2000, 9, 2)


def test_a_fixture_result_without_sources_is_rejected() -> None:
    with pytest.raises(ValidationError, match="at least one source"):
        FixturesFile.model_validate(fixtures_file(fixture(sources=[])))


def test_a_null_result_requires_verify_pending() -> None:
    with pytest.raises(ValidationError, match="result is null"):
        FixturesFile.model_validate(fixtures_file(fixture(result=None)))

    FixturesFile.model_validate(fixtures_file(fixture(result=None, verify="pending")))


def test_a_negative_score_is_rejected() -> None:
    with pytest.raises(ValidationError, match="goals_for"):
        FixturesFile.model_validate(
            fixtures_file(fixture(result={"goals_for": -1, "goals_against": 0}))
        )


def test_a_fixture_needs_either_a_round_or_a_stage() -> None:
    with pytest.raises(ValidationError, match="round or a stage"):
        FixturesFile.model_validate(fixtures_file(fixture(round=None)))
    with pytest.raises(ValidationError, match="round or a stage"):
        FixturesFile.model_validate(fixtures_file(fixture(stage="final")))


def test_a_knockout_fixture_with_penalties_parses() -> None:
    parsed = FixturesFile.model_validate(
        fixtures_file(
            fixture(
                id="f02",
                competition="copa",
                round=None,
                stage="final",
                venue="neutral",
                result={
                    "goals_for": 1,
                    "goals_against": 1,
                    "extra_time": True,
                    "penalties_for": 4,
                    "penalties_against": 3,
                },
            )
        )
    )

    assert parsed.fixtures[0].result is not None
    assert parsed.fixtures[0].result.penalties_for == 4


def test_penalties_need_both_scores() -> None:
    with pytest.raises(ValidationError, match="penalties"):
        FixturesFile.model_validate(
            fixtures_file(
                fixture(
                    round=None,
                    stage="final",
                    result={"goals_for": 1, "goals_against": 1, "penalties_for": 4},
                )
            )
        )


def test_duplicate_fixture_ids_are_rejected() -> None:
    with pytest.raises(ValidationError, match="duplicate fixture id"):
        FixturesFile.model_validate(fixtures_file(fixture(), fixture(round=2)))


# --------------------------------------------------------------------------- standings
def row(club: str, position: int, **overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "club_season": club,
        "position": position,
        "played": 2,
        "won": 1,
        "drawn": 1,
        "lost": 0,
        "goals_for": 3,
        "goals_against": 1,
        "points": 4,
    }
    data.update(overrides)
    return data


def standings_file(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "schema_version": 1,
        "cutoffs": [
            {
                "block": "b1",
                "competition": "liga",
                "date": date(2000, 9, 30),
                "table": [row(_OWN, 1), row(_RIVAL, 2, won=0, drawn=1, lost=1, points=1)],
                "sources": _SRC,
                "verify": "ok",
            }
        ],
        "ties": [
            {
                "competition": "copa",
                "stage": "semi",
                "clubs": [_OWN, _RIVAL],
                "winner": _OWN,
                "aggregate": "3-2",
                "sources": _SRC,
                "verify": "ok",
            }
        ],
    }
    data.update(overrides)
    return data


def test_valid_standings_parse() -> None:
    parsed = StandingsFile.model_validate(standings_file())

    assert parsed.cutoffs[0].table[0].club_season == _OWN


def test_a_row_whose_results_do_not_add_up_is_rejected() -> None:
    data = standings_file()
    data["cutoffs"][0]["table"][0]["played"] = 5

    with pytest.raises(ValidationError, match="played"):
        StandingsFile.model_validate(data)


def test_a_table_with_non_consecutive_positions_is_rejected() -> None:
    data = standings_file()
    data["cutoffs"][0]["table"][1]["position"] = 3

    with pytest.raises(ValidationError, match="positions"):
        StandingsFile.model_validate(data)


def test_a_table_not_ordered_by_points_is_rejected() -> None:
    data = standings_file()
    data["cutoffs"][0]["table"][1]["points"] = 9

    with pytest.raises(ValidationError, match="points"):
        StandingsFile.model_validate(data)


def test_a_standings_cutoff_without_sources_is_rejected() -> None:
    data = standings_file()
    data["cutoffs"][0]["sources"] = []

    with pytest.raises(ValidationError, match="at least one source"):
        StandingsFile.model_validate(data)


def test_a_tie_winner_must_be_one_of_its_clubs() -> None:
    data = standings_file()
    data["ties"][0]["winner"] = "other-fc-2000-01"

    with pytest.raises(ValidationError, match="winner"):
        StandingsFile.model_validate(data)


def test_duplicate_cutoffs_for_the_same_block_and_competition_are_rejected() -> None:
    data = standings_file()
    data["cutoffs"].append(deepcopy(data["cutoffs"][0]))

    with pytest.raises(ValidationError, match="duplicate cutoff"):
        StandingsFile.model_validate(data)


# --------------------------------------------------------------------------- dilemmas
def dilemma(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": "d01",
        "block": "b1",
        "title": "A dilemma",
        "prompt": "What do you do?",
        "options": [
            {"id": "a", "label": "Option A", "effects": [{"type": "morale", "delta": 5}]},
            {"id": "b", "label": "Option B", "effects": []},
        ],
        "historical_option": {"option": "a", "sources": _SRC, "verify": "ok"},
    }
    data.update(overrides)
    return data


def dilemmas_file(*items: dict[str, Any]) -> dict[str, Any]:
    return {"schema_version": 1, "dilemmas": list(items) or [dilemma()]}


def test_a_valid_dilemma_parses() -> None:
    parsed = DilemmasFile.model_validate(dilemmas_file())

    assert parsed.dilemmas[0].historical_option.option == "a"


def test_a_dilemma_needs_a_historical_option() -> None:
    data = dilemma()
    del data["historical_option"]

    with pytest.raises(ValidationError, match="historical_option"):
        DilemmasFile.model_validate(dilemmas_file(data))


def test_the_historical_option_must_be_one_of_the_options() -> None:
    with pytest.raises(ValidationError, match="historical_option"):
        DilemmasFile.model_validate(
            dilemmas_file(
                dilemma(historical_option={"option": "z", "sources": _SRC, "verify": "ok"})
            )
        )


def test_the_historical_option_needs_sources() -> None:
    with pytest.raises(ValidationError, match="at least one source"):
        DilemmasFile.model_validate(
            dilemmas_file(dilemma(historical_option={"option": "a", "sources": [], "verify": "ok"}))
        )


def test_a_dilemma_needs_between_two_and_four_options() -> None:
    with pytest.raises(ValidationError, match="options"):
        DilemmasFile.model_validate(dilemmas_file(dilemma(options=[{"id": "a", "label": "x"}])))


def test_duplicate_option_ids_are_rejected() -> None:
    options = [{"id": "a", "label": "x"}, {"id": "a", "label": "y"}]

    with pytest.raises(ValidationError, match="duplicate option id"):
        DilemmasFile.model_validate(dilemmas_file(dilemma(options=options)))


def test_an_option_with_an_unknown_effect_is_rejected() -> None:
    options = [
        {"id": "a", "label": "x", "effects": [{"type": "win_the_league"}]},
        {"id": "b", "label": "y"},
    ]

    with pytest.raises(ValidationError, match="union_tag_invalid"):
        DilemmasFile.model_validate(dilemmas_file(dilemma(options=options)))


def test_duplicate_dilemma_ids_are_rejected() -> None:
    with pytest.raises(ValidationError, match="duplicate dilemma id"):
        DilemmasFile.model_validate(dilemmas_file(dilemma(), dilemma()))


# --------------------------------------------------------------------------- texts
def text(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": "presentation.intro",
        "kind": "presentation",
        "body": "Welcome, manager.",
        "status": "reviewed",
        "reviewed_by": "A. Reviewer",
    }
    data.update(overrides)
    return data


def texts_file(*items: dict[str, Any]) -> dict[str, Any]:
    return {"schema_version": 1, "texts": list(items) or [text()]}


def test_valid_texts_parse() -> None:
    parsed = TextsFile.model_validate(texts_file(text(), text(id="event.one", kind="event")))

    assert len(parsed.texts) == 2


def test_a_reviewed_text_needs_reviewed_by() -> None:
    with pytest.raises(ValidationError, match="reviewed_by"):
        TextsFile.model_validate(texts_file(text(reviewed_by=None)))


def test_a_draft_text_does_not_need_reviewed_by() -> None:
    parsed = TextsFile.model_validate(texts_file(text(status="draft", reviewed_by=None)))

    assert parsed.texts[0].status == "draft"


def test_an_unknown_text_status_is_rejected() -> None:
    with pytest.raises(ValidationError, match="status"):
        TextsFile.model_validate(texts_file(text(status="final")))


def test_duplicate_text_ids_are_rejected() -> None:
    with pytest.raises(ValidationError, match="duplicate text id"):
        TextsFile.model_validate(texts_file(text(), text()))
