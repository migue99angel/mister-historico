"""Loading and validating a whole content tree (schema, integrity, release mode)."""

import shutil
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

import pytest
import yaml

from mister.catalog.infrastructure.content_schema import (
    ContentIssue,
    ContentTree,
    ContentValidationError,
    load_content_tree,
)

FIXTURE_ROOT = Path(__file__).parent.parent / "fixtures" / "content"
SEASON = "seasons/test-fc-2000-01"
OWN = "test-fc-2000-01"
SQUAD = f"club-seasons/{OWN}/squad.yaml"
Mutation = Callable[[dict[str, Any]], None]


@pytest.fixture
def root(tmp_path: Path) -> Path:
    target = tmp_path / "content"
    shutil.copytree(FIXTURE_ROOT, target)
    return target


def edit(root: Path, relative: str, mutate: Mutation) -> None:
    path = root / relative
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    mutate(data)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def issues_of(root: Path, *, release: bool = False) -> list[ContentIssue]:
    with pytest.raises(ContentValidationError) as raised:
        load_content_tree(root, release=release)
    return list(raised.value.issues)


def assert_issue(
    issues: list[ContentIssue], path: str, field_part: str = "", message_part: str = ""
) -> None:
    found = [
        i for i in issues if i.path == path and field_part in i.field and message_part in i.message
    ]
    assert found, f"no issue at {path} / {field_part} / {message_part} in:\n" + "\n".join(
        map(str, issues)
    )


# --------------------------------------------------------------------------- the happy path
def test_the_synthetic_test_fc_tree_is_valid(root: Path) -> None:
    tree = load_content_tree(root, release=False)

    assert isinstance(tree, ContentTree)
    assert OWN in tree.seasons
    assert len(tree.clubs) == 10


def test_the_synthetic_test_fc_tree_passes_release_validation(root: Path) -> None:
    tree = load_content_tree(root, release=True)

    assert set(tree.squads) >= {OWN, "_market-2000-01"}
    assert set(tree.aggregates) == {
        "placeholder-town-2000-01",
        "overseas-fc-2000-01",
        "abroad-athletic-2000-01",
        "faraway-city-2000-01",
    }


def test_the_synthetic_season_has_ten_dilemmas_that_use_every_effect_type(root: Path) -> None:
    tree = load_content_tree(root, release=True)

    dilemmas = tree.seasons[OWN].dilemmas.dilemmas
    types = {e.type for d in dilemmas for o in d.options for e in o.effects}

    assert len(dilemmas) == 10
    assert types == {
        "morale", "player_morale", "sign_player", "sell_player", "set_tactic",
        "competition_priority", "board_confidence", "youth_minutes", "injury", "fitness",
    }  # fmt: skip


def test_the_synthetic_league_has_six_clubs_with_full_squads(root: Path) -> None:
    tree = load_content_tree(root, release=True)

    league_squads = [tree.squads[c] for c in tree.seasons[OWN].season.competitions[0].participants]
    assert len(league_squads) == 6
    assert all(18 <= len(s.players) <= 22 for s in league_squads)


# --------------------------------------------------------------------------- schema errors
def test_a_rating_of_100_reports_the_file_and_field(root: Path) -> None:
    edit(root, SQUAD, lambda d: d["players"][2].update(rating=100))

    assert_issue(issues_of(root), SQUAD, "players.2.rating")


def test_a_player_without_sources_reports_the_file_and_field(root: Path) -> None:
    edit(root, SQUAD, lambda d: d["players"][2].update(sources=[]))

    assert_issue(issues_of(root), SQUAD, "players.2", "at least one source")


def test_a_key_player_without_rationale_is_reported(root: Path) -> None:
    def mutate(d: dict[str, Any]) -> None:
        d["players"][2].pop("rating_rationale", None)
        d["players"][2]["key"] = True

    edit(root, "club-seasons/sample-united-2000-01/squad.yaml", mutate)

    assert_issue(
        issues_of(root),
        "club-seasons/sample-united-2000-01/squad.yaml",
        "players",
        "rating_rationale",
    )


def test_an_unknown_effect_type_is_reported(root: Path) -> None:
    edit(
        root,
        f"{SEASON}/dilemmas.yaml",
        lambda d: d["dilemmas"][0]["options"][0]["effects"].append({"type": "teleport"}),
    )

    assert_issue(issues_of(root), f"{SEASON}/dilemmas.yaml", "dilemmas.0.options.0.effects")


def test_all_errors_are_accumulated_not_just_the_first(root: Path) -> None:
    edit(root, SQUAD, lambda d: d["players"][2].update(rating=100))
    edit(root, f"{SEASON}/texts.yaml", lambda d: d["texts"][0].update(status="final"))
    edit(root, "clubs/mock-city.yaml", lambda d: d["colors"].update(primary="red"))

    issues = issues_of(root)

    assert_issue(issues, SQUAD, "players.2.rating")
    assert_issue(issues, f"{SEASON}/texts.yaml", "texts.0.status")
    assert_issue(issues, "clubs/mock-city.yaml", "colors.primary")


def test_the_error_message_lists_every_issue_with_path_and_field(root: Path) -> None:
    edit(root, SQUAD, lambda d: d["players"][2].update(rating=100))
    edit(root, f"{SEASON}/texts.yaml", lambda d: d["texts"][0].update(status="final"))

    with pytest.raises(ContentValidationError) as raised:
        load_content_tree(root, release=False)

    message = str(raised.value)
    assert f"{SQUAD}: players.2.rating" in message
    assert f"{SEASON}/texts.yaml: texts.0.status" in message


def test_invalid_yaml_syntax_is_reported(root: Path) -> None:
    (root / "clubs" / "mock-city.yaml").write_text("club_id: [unclosed\n", encoding="utf-8")

    assert_issue(issues_of(root), "clubs/mock-city.yaml", "", "YAML")


def test_duplicate_yaml_keys_are_reported(root: Path) -> None:
    path = root / "clubs" / "mock-city.yaml"
    path.write_text(path.read_text(encoding="utf-8") + "name: Again\n", encoding="utf-8")

    assert_issue(issues_of(root), "clubs/mock-city.yaml", "name", "duplicate")


def test_a_missing_season_file_is_reported(root: Path) -> None:
    (root / SEASON / "texts.yaml").unlink()

    assert_issue(issues_of(root), f"{SEASON}/texts.yaml", "", "missing")


def test_a_club_season_directory_must_match_its_id(root: Path) -> None:
    edit(
        root,
        "club-seasons/mock-city-2000-01/squad.yaml",
        lambda d: d.update(club_season="dummy-rovers-2000-01", club="dummy-rovers"),
    )

    assert_issue(issues_of(root), "club-seasons/mock-city-2000-01/squad.yaml", "club_season")


def test_a_club_season_whose_club_has_no_file_is_reported(root: Path) -> None:
    (root / "clubs" / "mock-city.yaml").unlink()

    assert_issue(issues_of(root), "club-seasons/mock-city-2000-01/squad.yaml", "club", "mock-city")


def test_a_missing_root_is_reported(tmp_path: Path) -> None:
    assert_issue(issues_of(tmp_path / "nope"), ".", "", "does not exist")


# --------------------------------------------------------------------------- referential integrity
def test_sign_player_of_an_unknown_player_is_reported(root: Path) -> None:
    edit(
        root,
        f"{SEASON}/dilemmas.yaml",
        lambda d: d["dilemmas"][0]["options"][0]["effects"][0].update(player_id="ghost-99"),
    )

    assert_issue(
        issues_of(root),
        f"{SEASON}/dilemmas.yaml",
        "dilemmas.0.options.0.effects.0.player_id",
        "ghost-99",
    )


def test_sign_player_from_a_squad_that_does_not_have_him_is_reported(root: Path) -> None:
    edit(
        root,
        f"{SEASON}/dilemmas.yaml",
        lambda d: d["dilemmas"][0]["options"][1]["effects"][0].update(
            from_club_season="mock-city-2000-01"
        ),
    )

    assert_issue(
        issues_of(root),
        f"{SEASON}/dilemmas.yaml",
        "dilemmas.0.options.1.effects.0.from_club_season",
        "not in the squad",
    )


def test_sign_player_from_an_unknown_club_season_is_reported(root: Path) -> None:
    edit(
        root,
        f"{SEASON}/dilemmas.yaml",
        lambda d: d["dilemmas"][0]["options"][1]["effects"][0].update(
            from_club_season="nobody-2000-01"
        ),
    )

    assert_issue(issues_of(root), f"{SEASON}/dilemmas.yaml", "from_club_season", "nobody-2000-01")


def test_sell_player_to_an_unknown_club_season_is_reported(root: Path) -> None:
    edit(
        root,
        f"{SEASON}/dilemmas.yaml",
        lambda d: d["dilemmas"][4]["options"][0]["effects"][0].update(
            to_club_season="nobody-2000-01"
        ),
    )

    assert_issue(issues_of(root), f"{SEASON}/dilemmas.yaml", "to_club_season", "nobody-2000-01")


def test_an_effect_on_a_player_outside_the_own_squad_is_reported(root: Path) -> None:
    edit(
        root,
        f"{SEASON}/dilemmas.yaml",
        lambda d: d["dilemmas"][2]["options"][0]["effects"][0].update(player_id="smu-03"),
    )

    assert_issue(issues_of(root), f"{SEASON}/dilemmas.yaml", "player_id", "smu-03")


def test_a_priority_effect_on_an_unknown_competition_is_reported(root: Path) -> None:
    edit(
        root,
        f"{SEASON}/dilemmas.yaml",
        lambda d: d["dilemmas"][3]["options"][0]["effects"][0].update(competition_id="nope"),
    )

    assert_issue(issues_of(root), f"{SEASON}/dilemmas.yaml", "competition_id", "nope")


def test_an_injury_outside_the_season_is_reported(root: Path) -> None:
    edit(
        root,
        f"{SEASON}/dilemmas.yaml",
        lambda d: d["dilemmas"][5]["options"][0]["effects"][0].update(date=date(2003, 1, 1)),
    )

    assert_issue(issues_of(root), f"{SEASON}/dilemmas.yaml", "date", "outside")


def test_a_fixture_against_an_unknown_club_season_is_reported(root: Path) -> None:
    edit(
        root,
        f"{SEASON}/fixtures.yaml",
        lambda d: d["fixtures"][0].update(opponent="nobody-2000-01"),
    )

    assert_issue(
        issues_of(root), f"{SEASON}/fixtures.yaml", "fixtures.0.opponent", "nobody-2000-01"
    )


def test_a_fixture_in_an_unknown_competition_is_reported(root: Path) -> None:
    edit(root, f"{SEASON}/fixtures.yaml", lambda d: d["fixtures"][0].update(competition="nope"))

    assert_issue(issues_of(root), f"{SEASON}/fixtures.yaml", "fixtures.0.competition", "nope")


def test_a_fixture_against_a_non_participant_is_reported(root: Path) -> None:
    edit(
        root,
        f"{SEASON}/fixtures.yaml",
        lambda d: d["fixtures"][0].update(opponent="placeholder-town-2000-01"),
    )

    assert_issue(issues_of(root), f"{SEASON}/fixtures.yaml", "fixtures.0.opponent", "participant")


def test_a_fixture_outside_every_block_is_reported(root: Path) -> None:
    edit(
        root,
        f"{SEASON}/fixtures.yaml",
        lambda d: d["fixtures"][0].update(date=date(2000, 7, 15)),
    )

    assert_issue(issues_of(root), f"{SEASON}/fixtures.yaml", "fixtures.0.date", "block")


def test_a_fixture_in_an_unknown_stage_is_reported(root: Path) -> None:
    def mutate(d: dict[str, Any]) -> None:
        cup = next(f for f in d["fixtures"] if f["competition"] == "copa-test")
        cup["stage"] = "quarterfinal"

    edit(root, f"{SEASON}/fixtures.yaml", mutate)

    assert_issue(issues_of(root), f"{SEASON}/fixtures.yaml", "stage", "quarterfinal")


def test_a_double_round_robin_league_needs_every_match_of_the_own_team(root: Path) -> None:
    edit(
        root,
        f"{SEASON}/fixtures.yaml",
        lambda d: d["fixtures"].remove(next(f for f in d["fixtures"] if f["id"] == "tfc-liga-10")),
    )

    assert_issue(issues_of(root), f"{SEASON}/fixtures.yaml", "fixtures", "10")


def test_a_league_opponent_must_be_met_once_at_home_and_once_away(root: Path) -> None:
    def mutate(d: dict[str, Any]) -> None:
        first = next(f for f in d["fixtures"] if f["id"] == "tfc-liga-01")
        first["venue"] = "away" if first["venue"] == "home" else "home"

    edit(root, f"{SEASON}/fixtures.yaml", mutate)

    assert_issue(issues_of(root), f"{SEASON}/fixtures.yaml", "fixtures", "home and once away")


def test_the_playable_squad_needs_a_rationale_for_every_player(root: Path) -> None:
    edit(root, SQUAD, lambda d: d["players"][0].pop("rating_rationale"))

    assert_issue(issues_of(root), SQUAD, "players.0.rating_rationale", "playable")


def test_a_player_in_two_squads_on_the_same_date_is_reported(root: Path) -> None:
    edit(
        root,
        "club-seasons/demo-athletic-2000-01/squad.yaml",
        lambda d: d["players"][-1].pop("left_on"),
    )

    assert_issue(
        issues_of(root),
        "club-seasons/mock-city-2000-01/squad.yaml",
        "players",
        "xfer-01 also belongs to demo-athletic-2000-01",
    )


def test_a_dated_transfer_between_squads_is_valid(root: Path) -> None:
    load_content_tree(root, release=False)


def test_a_player_keeps_the_same_name_across_squads(root: Path) -> None:
    edit(
        root,
        "club-seasons/mock-city-2000-01/squad.yaml",
        lambda d: d["players"][-1].update(display_name="Someone Else"),
    )

    assert_issue(issues_of(root), "club-seasons/mock-city-2000-01/squad.yaml", "players", "xfer-01")


def test_a_league_participant_without_a_squad_is_reported(root: Path) -> None:
    def mutate(d: dict[str, Any]) -> None:
        d["competitions"][0]["participants"][1] = "placeholder-town-2000-01"

    edit(root, f"{SEASON}/season.yaml", mutate)

    assert_issue(issues_of(root), f"{SEASON}/season.yaml", "competitions.0.participants", "squad")


def test_a_competition_participant_that_does_not_exist_is_reported(root: Path) -> None:
    edit(
        root,
        f"{SEASON}/season.yaml",
        lambda d: d["competitions"][1]["participants"].__setitem__(3, "nobody-2000-01"),
    )

    assert_issue(issues_of(root), f"{SEASON}/season.yaml", "competitions.1.participants", "nobody")


def test_a_season_whose_own_club_season_has_no_squad_is_reported(root: Path) -> None:
    edit(root, f"{SEASON}/season.yaml", lambda d: d.update(club_season="placeholder-town-2000-01"))

    assert any(i.path == f"{SEASON}/season.yaml" for i in issues_of(root))


# --------------------------------------------------------------------------- dilemmas
def test_a_block_without_dilemmas_is_reported(root: Path) -> None:
    def mutate(d: dict[str, Any]) -> None:
        for dilemma in d["dilemmas"]:
            if dilemma["block"] == "b5":
                dilemma["block"] = "b4"

    edit(root, f"{SEASON}/dilemmas.yaml", mutate)

    assert_issue(issues_of(root), f"{SEASON}/dilemmas.yaml", "dilemmas", "block b5 has")


def test_a_block_with_more_than_three_dilemmas_is_reported(root: Path) -> None:
    def mutate(d: dict[str, Any]) -> None:
        d["dilemmas"][2]["block"] = "b1"
        d["dilemmas"][3]["block"] = "b1"

    edit(root, f"{SEASON}/dilemmas.yaml", mutate)

    assert_issue(issues_of(root), f"{SEASON}/dilemmas.yaml", "dilemmas", "block b1 has")


def test_more_than_twelve_dilemmas_in_total_are_reported(root: Path) -> None:
    def mutate(d: dict[str, Any]) -> None:
        for i, block in enumerate(["b3", "b4", "b5"]):
            extra = {**d["dilemmas"][0], "id": f"x{i}", "block": block}
            d["dilemmas"].append(extra)

    edit(root, f"{SEASON}/dilemmas.yaml", mutate)

    assert_issue(issues_of(root), f"{SEASON}/dilemmas.yaml", "dilemmas", "between 8 and 12")


def test_fewer_than_eight_dilemmas_in_total_are_reported(root: Path) -> None:
    def mutate(d: dict[str, Any]) -> None:
        d["dilemmas"] = d["dilemmas"][:7]
        for dilemma in d["dilemmas"][6:]:
            dilemma["block"] = "b4"

    edit(root, f"{SEASON}/dilemmas.yaml", mutate)

    assert_issue(issues_of(root), f"{SEASON}/dilemmas.yaml", "dilemmas", "between 8 and 12")


def test_a_dilemma_in_an_unknown_block_is_reported(root: Path) -> None:
    edit(root, f"{SEASON}/dilemmas.yaml", lambda d: d["dilemmas"][0].update(block="b9"))

    assert_issue(issues_of(root), f"{SEASON}/dilemmas.yaml", "dilemmas.0.block", "b9")


# --------------------------------------------------------------------------- standings
def test_a_real_standings_row_must_match_the_own_fixtures(root: Path) -> None:
    def mutate(d: dict[str, Any]) -> None:
        first = next(f for f in d["fixtures"] if f["id"] == "tfc-liga-01")
        first["result"]["goals_for"] += 1

    edit(root, f"{SEASON}/fixtures.yaml", mutate)

    assert_issue(issues_of(root), f"{SEASON}/standings.yaml", "cutoffs", "fixtures")


def test_every_block_needs_a_standings_cutoff_for_each_league(root: Path) -> None:
    edit(root, f"{SEASON}/standings.yaml", lambda d: d["cutoffs"].pop(2))

    assert_issue(issues_of(root), f"{SEASON}/standings.yaml", "cutoffs", "b3")


def test_a_cutoff_date_must_be_the_end_of_its_block(root: Path) -> None:
    edit(
        root,
        f"{SEASON}/standings.yaml",
        lambda d: d["cutoffs"][0].update(date=date(2000, 9, 29)),
    )

    assert_issue(issues_of(root), f"{SEASON}/standings.yaml", "cutoffs.0.date", "end")


def test_a_standings_table_must_list_every_participant(root: Path) -> None:
    def mutate(d: dict[str, Any]) -> None:
        table = d["cutoffs"][0]["table"]
        table[-1]["club_season"] = "placeholder-town-2000-01"

    edit(root, f"{SEASON}/standings.yaml", mutate)

    assert_issue(issues_of(root), f"{SEASON}/standings.yaml", "cutoffs.0.table", "participants")


def test_real_league_goals_must_match_the_final_table(root: Path) -> None:
    edit(
        root, SQUAD, lambda d: d["real_league"].update(goals_for=d["real_league"]["goals_for"] + 1)
    )

    assert_issue(issues_of(root), SQUAD, "real_league.goals_for", "standings")


def test_a_tie_in_an_unknown_stage_is_reported(root: Path) -> None:
    edit(root, f"{SEASON}/standings.yaml", lambda d: d["ties"][0].update(stage="nope"))

    assert_issue(issues_of(root), f"{SEASON}/standings.yaml", "ties.0.stage", "nope")


def test_a_tie_between_non_participants_is_reported(root: Path) -> None:
    edit(
        root,
        f"{SEASON}/standings.yaml",
        lambda d: d["ties"][0].update(clubs=["test-fc-2000-01", "demo-athletic-2000-01"]),
    )

    assert_issue(issues_of(root), f"{SEASON}/standings.yaml", "ties.0.clubs", "participant")


# --------------------------------------------------------------------------- historical outcome
def test_a_league_outcome_needs_a_final_position(root: Path) -> None:
    edit(
        root,
        f"{SEASON}/season.yaml",
        lambda d: d["historical_outcome"][0].update(final_position=None),
    )

    assert_issue(issues_of(root), f"{SEASON}/season.yaml", "historical_outcome.0", "final_position")


def test_every_competition_needs_one_historical_outcome(root: Path) -> None:
    edit(root, f"{SEASON}/season.yaml", lambda d: d["historical_outcome"].pop(1))

    assert_issue(issues_of(root), f"{SEASON}/season.yaml", "historical_outcome", "copa-test")


# --------------------------------------------------------------------------- release mode
def test_pending_data_is_accepted_outside_release_mode(root: Path) -> None:
    edit(root, SQUAD, lambda d: d["players"][2].update(age=None, verify="pending"))

    load_content_tree(root, release=False)


def test_pending_data_is_rejected_in_release_mode(root: Path) -> None:
    edit(root, SQUAD, lambda d: d["players"][2].update(age=None, verify="pending"))

    assert_issue(issues_of(root, release=True), SQUAD, "players.2.verify", "pending")


def test_pending_standings_and_fixtures_are_rejected_in_release_mode(root: Path) -> None:
    edit(
        root,
        f"{SEASON}/fixtures.yaml",
        lambda d: d["fixtures"][3].update(verify="pending"),
    )
    edit(
        root,
        f"{SEASON}/dilemmas.yaml",
        lambda d: d["dilemmas"][1]["historical_option"].update(verify="pending"),
    )

    issues = issues_of(root, release=True)

    assert_issue(issues, f"{SEASON}/fixtures.yaml", "fixtures.3.verify", "pending")
    assert_issue(
        issues, f"{SEASON}/dilemmas.yaml", "dilemmas.1.historical_option.verify", "pending"
    )


def test_draft_texts_are_accepted_outside_release_mode(root: Path) -> None:
    edit(
        root,
        f"{SEASON}/texts.yaml",
        lambda d: d["texts"][0].update(status="draft", reviewed_by=None),
    )

    load_content_tree(root, release=False)


def test_draft_texts_are_rejected_in_release_mode(root: Path) -> None:
    edit(
        root,
        f"{SEASON}/texts.yaml",
        lambda d: d["texts"][0].update(status="draft", reviewed_by=None),
    )

    assert_issue(issues_of(root, release=True), f"{SEASON}/texts.yaml", "texts.0.status", "draft")


def test_release_issues_are_added_to_the_other_issues(root: Path) -> None:
    edit(root, SQUAD, lambda d: d["players"][2].update(age=None, verify="pending"))
    edit(root, f"{SEASON}/texts.yaml", lambda d: d["texts"][1].update(status="draft"))
    edit(root, "clubs/mock-city.yaml", lambda d: d["colors"].update(primary="red"))

    issues = issues_of(root, release=True)

    assert {i.path for i in issues} >= {SQUAD, f"{SEASON}/texts.yaml", "clubs/mock-city.yaml"}


# --------------------------------------------------------------------------- schema v2 additions
FIXTURES = f"{SEASON}/fixtures.yaml"
STANDINGS = f"{SEASON}/standings.yaml"
SEASON_FILE = f"{SEASON}/season.yaml"
DILEMMAS = f"{SEASON}/dilemmas.yaml"


def fixture_of(data: dict[str, Any], fixture_id: str) -> dict[str, Any]:
    found: dict[str, Any] = next(f for f in data["fixtures"] if f["id"] == fixture_id)
    return found


def test_the_synthetic_season_has_all_four_competition_kinds_and_a_group_stage(root: Path) -> None:
    tree = load_content_tree(root, release=True)

    competitions = tree.seasons[OWN].season.competitions

    assert [c.kind for c in competitions] == ["league", "cup", "super_cup", "continental_cup"]
    assert any(s.round == "group_stage" for s in getattr(competitions[3], "stages", ()))


def test_sign_player_of_a_rival_player_without_from_club_season_is_reported(root: Path) -> None:
    edit(
        root,
        DILEMMAS,
        lambda d: d["dilemmas"][0]["options"][1]["effects"][0].pop("from_club_season"),
    )

    assert_issue(
        issues_of(root),
        DILEMMAS,
        "dilemmas.0.options.1.effects.0.player_id",
        "belongs to sample-united-2000-01",
    )


def test_sign_player_of_a_player_already_in_the_own_squad_is_reported(root: Path) -> None:
    edit(
        root,
        DILEMMAS,
        lambda d: d["dilemmas"][0]["options"][0]["effects"][0].update(player_id="tfc-03"),
    )

    assert_issue(issues_of(root), DILEMMAS, "player_id", "already in the own squad")


@pytest.mark.parametrize("day", [date(2000, 6, 30), date(2001, 7, 1)])
def test_an_injury_effect_outside_the_season_is_reported(root: Path, day: date) -> None:
    edit(
        root,
        DILEMMAS,
        lambda d: d["dilemmas"][5]["options"][0]["effects"][0].update(date=day),
    )

    assert_issue(issues_of(root), DILEMMAS, "date", "outside the allowed window")


def test_a_forced_injury_of_an_unknown_player_is_reported(root: Path) -> None:
    edit(root, SEASON_FILE, lambda d: d["forced_events"][0].update(player_id="ghost-1"))

    assert_issue(issues_of(root), SEASON_FILE, "forced_events.0.player_id", "ghost-1")


def test_a_forced_injury_outside_the_season_is_reported(root: Path) -> None:
    edit(root, SEASON_FILE, lambda d: d["forced_events"][0].update(date=date(2002, 1, 1)))

    assert_issue(issues_of(root), SEASON_FILE, "", "does not overlap the season blocks")


# --- outcomes against the real tables and brackets
def test_a_league_position_that_contradicts_the_table_is_reported(root: Path) -> None:
    edit(root, SEASON_FILE, lambda d: d["historical_outcome"][0].update(final_position=1))

    assert_issue(issues_of(root), SEASON_FILE, "historical_outcome.0.final_position", "contradicts")


def test_a_league_title_that_contradicts_the_table_is_reported(root: Path) -> None:
    edit(root, SEASON_FILE, lambda d: d["historical_outcome"][0].update(champion=True))

    assert_issue(issues_of(root), SEASON_FILE, "historical_outcome.0.champion", "contradicts")


def test_a_cup_outcome_needs_a_champion_or_an_elimination(root: Path) -> None:
    edit(root, SEASON_FILE, lambda d: d["historical_outcome"][1].update(champion=False))

    assert_issue(issues_of(root), SEASON_FILE, "historical_outcome.1", "champion or eliminated_in")


def test_a_cup_elimination_that_contradicts_the_bracket_is_reported(root: Path) -> None:
    edit(
        root,
        SEASON_FILE,
        lambda d: d["historical_outcome"][1].update(champion=False, eliminated_in="semifinal"),
    )

    assert_issue(issues_of(root), SEASON_FILE, "historical_outcome.1", "contradicts")


def test_a_continental_title_that_contradicts_the_final_is_reported(root: Path) -> None:
    edit(
        root,
        SEASON_FILE,
        lambda d: d["historical_outcome"][3].update(champion=True, eliminated_in=None),
    )

    assert_issue(issues_of(root), SEASON_FILE, "historical_outcome.3.champion", "contradicts")


def test_a_group_stage_elimination_that_contradicts_the_group_table_is_reported(
    root: Path,
) -> None:
    edit(root, SEASON_FILE, lambda d: d["historical_outcome"][3].update(eliminated_in="groups"))

    assert_issue(issues_of(root), SEASON_FILE, "historical_outcome.3.eliminated_in", "contradicts")


# --- knockout legs, order and same-day fixtures
def test_a_two_legged_tie_with_only_the_first_leg_is_reported(root: Path) -> None:
    edit(
        root,
        FIXTURES,
        lambda d: d["fixtures"].remove(fixture_of(d, "tfc-copa-sf-2")),
    )

    assert_issue(issues_of(root), FIXTURES, "fixtures", "only the first leg")


def test_a_two_legged_tie_with_two_first_legs_is_reported(root: Path) -> None:
    edit(root, FIXTURES, lambda d: fixture_of(d, "tfc-copa-sf-2").update(leg=1))

    assert_issue(issues_of(root), FIXTURES, "fixtures", "same leg")


def test_a_two_legged_fixture_needs_its_leg(root: Path) -> None:
    edit(root, FIXTURES, lambda d: fixture_of(d, "tfc-copa-sf-2").pop("leg"))

    assert_issue(issues_of(root), FIXTURES, ".leg", "leg is required")


def test_a_final_before_the_semifinal_is_reported(root: Path) -> None:
    edit(root, FIXTURES, lambda d: fixture_of(d, "tfc-copa-final").update(date=date(2000, 11, 1)))

    assert_issue(issues_of(root), FIXTURES, "fixtures", "starts before stage")


def test_two_own_fixtures_on_the_same_day_are_reported(root: Path) -> None:
    edit(root, FIXTURES, lambda d: fixture_of(d, "tfc-copa-sf-1").update(date=date(2000, 11, 4)))

    assert_issue(issues_of(root), FIXTURES, "", "same date")


# --- group stage
def test_a_group_stage_needs_all_the_matches_of_the_own_team(root: Path) -> None:
    edit(root, FIXTURES, lambda d: d["fixtures"].remove(fixture_of(d, "tfc-cont-g6")))

    assert_issue(issues_of(root), FIXTURES, "fixtures", "expected 6")


def test_a_group_fixture_in_an_unknown_group_is_reported(root: Path) -> None:
    edit(root, FIXTURES, lambda d: fixture_of(d, "tfc-cont-g1").update(group="z"))

    assert_issue(issues_of(root), FIXTURES, ".group", "unknown group")


def test_a_group_fixture_against_a_team_outside_the_group_is_reported(root: Path) -> None:
    edit(
        root,
        FIXTURES,
        lambda d: fixture_of(d, "tfc-cont-g1").update(opponent="sample-united-2000-01"),
    )

    assert_issue(issues_of(root), FIXTURES, ".opponent", "participant")


def test_every_group_needs_real_standings(root: Path) -> None:
    edit(
        root,
        STANDINGS,
        lambda d: d.update(cutoffs=[c for c in d["cutoffs"] if c.get("stage") != "groups"]),
    )

    assert_issue(issues_of(root), STANDINGS, "cutoffs", "has no standings")


def test_the_latest_group_table_must_be_complete(root: Path) -> None:
    def mutate(d: dict[str, Any]) -> None:
        groups = [c for c in d["cutoffs"] if c.get("stage") == "groups"]
        d["cutoffs"].remove(groups[-1])
        d["cutoffs"].remove(groups[-2])

    edit(root, STANDINGS, mutate)

    assert_issue(issues_of(root), STANDINGS, "cutoffs", "incomplete")


def test_a_group_table_must_match_the_own_group_fixtures(root: Path) -> None:
    edit(
        root,
        FIXTURES,
        lambda d: fixture_of(d, "tfc-cont-g1")["result"].update(goals_for=9),
    )

    assert_issue(issues_of(root), STANDINGS, "cutoffs", "own fixtures")


def test_a_group_table_must_list_the_teams_of_its_group(root: Path) -> None:
    def mutate(d: dict[str, Any]) -> None:
        group = next(c for c in d["cutoffs"] if c.get("stage") == "groups")
        group["table"][-1]["club_season"] = "mock-city-2000-01"

    edit(root, STANDINGS, mutate)

    assert_issue(issues_of(root), STANDINGS, "table", "participants")


# --- rival squads (P6)
def test_a_rival_squad_with_fewer_than_18_players_is_reported(root: Path) -> None:
    edit(
        root,
        "club-seasons/demo-athletic-2000-01/squad.yaml",
        lambda d: d.update(players=d["players"][:15]),
    )

    assert_issue(
        issues_of(root),
        "club-seasons/demo-athletic-2000-01/squad.yaml",
        "players",
        "between 18 and 22",
    )


def test_a_rival_squad_with_more_than_22_players_is_reported(root: Path) -> None:
    def mutate(d: dict[str, Any]) -> None:
        for i in range(4):
            extra = {**d["players"][-1], "player_id": f"dma-x{i}", "display_name": f"Extra {i}"}
            extra["alias_name"] = f"Alias X{i}"
            d["players"].append(extra)

    edit(root, "club-seasons/demo-athletic-2000-01/squad.yaml", mutate)

    assert_issue(
        issues_of(root),
        "club-seasons/demo-athletic-2000-01/squad.yaml",
        "players",
        "between 18 and 22",
    )


@pytest.mark.parametrize(("position", "minimum"), [("GK", 2), ("DF", 6), ("MF", 6), ("FW", 4)])
def test_a_rival_squad_needs_a_minimum_coverage_per_position(
    root: Path, position: str, minimum: int
) -> None:
    def mutate(d: dict[str, Any]) -> None:
        replacement = "DF" if position != "DF" else "MF"
        for player in d["players"]:
            if player["position"] == position:
                player["position"] = replacement

    edit(root, "club-seasons/dummy-rovers-2000-01/squad.yaml", mutate)

    assert_issue(
        issues_of(root),
        "club-seasons/dummy-rovers-2000-01/squad.yaml",
        "players",
        f"at least {minimum} {position}",
    )


def test_the_market_squad_is_exempt_from_the_rival_squad_rules(root: Path) -> None:
    load_content_tree(root, release=False)  # the market squad has 3 players


# --- real league of a rival (B5)
def test_a_real_league_of_another_competition_is_not_compared_with_the_standings(
    root: Path,
) -> None:
    def mutate(d: dict[str, Any]) -> None:
        d["real_league"]["competition_label"] = "Some Other League"
        d["real_league"]["goals_for"] += 5

    edit(root, "club-seasons/sample-united-2000-01/squad.yaml", mutate)

    load_content_tree(root, release=True)


# --- pending ratings (B1)
def test_a_pending_rating_is_accepted_outside_release_mode(root: Path) -> None:
    def mutate(d: dict[str, Any]) -> None:
        d["players"][2].update(rating=None, verify="pending")

    edit(root, "club-seasons/sample-united-2000-01/squad.yaml", mutate)

    load_content_tree(root, release=False)


def test_a_pending_rating_is_rejected_in_release_mode(root: Path) -> None:
    edit(root, SQUAD, lambda d: d["players"][2].update(rating=None, verify="pending"))

    assert_issue(issues_of(root, release=True), SQUAD, "players.2.verify", "pending")


def test_a_pending_playable_player_does_not_need_a_rationale_yet(root: Path) -> None:
    def mutate(d: dict[str, Any]) -> None:
        d["players"][2].pop("rating_rationale")
        d["players"][2].update(rating=None, verify="pending")

    edit(root, SQUAD, mutate)

    load_content_tree(root, release=False)


def test_a_pending_aggregate_is_rejected_in_release_mode(root: Path) -> None:
    path = "club-seasons/placeholder-town-2000-01/aggregate.yaml"
    edit(root, path, lambda d: d.update(attack=None, defense=None, verify="pending"))

    load_content_tree(root, release=False)
    assert_issue(issues_of(root, release=True), path, "verify", "pending")


def test_a_string_rating_in_a_yaml_file_is_rejected(root: Path) -> None:
    edit(root, SQUAD, lambda d: d["players"][2].update(rating="80"))

    assert_issue(issues_of(root), SQUAD, "players.2.rating")


# --------------------------------------------------------------------------- round 3
def test_both_legs_of_a_tie_at_home_are_reported(root: Path) -> None:
    edit(root, FIXTURES, lambda d: fixture_of(d, "tfc-copa-sf-1").update(venue="home"))

    assert_issue(issues_of(root), FIXTURES, "fixtures", "one leg at home and the other away")


def test_leg_two_before_leg_one_is_reported(root: Path) -> None:
    def mutate(d: dict[str, Any]) -> None:
        fixture_of(d, "tfc-copa-sf-1")["date"] = date(2001, 2, 20)

    edit(root, FIXTURES, mutate)

    assert_issue(issues_of(root), FIXTURES, "fixtures", "leg 1 must be played before leg 2")


@pytest.mark.parametrize("day", [date(2000, 11, 30), date(2001, 6, 1)])
def test_an_injury_effect_outside_its_block_window_is_reported(root: Path, day: date) -> None:
    # d06 belongs to b3 (2000-12-01..2001-01-31): it cannot start before the block starts
    # nor after the last block of the season ends.
    edit(
        root,
        DILEMMAS,
        lambda d: d["dilemmas"][5]["options"][0]["effects"][0].update(date=day),
    )

    assert_issue(issues_of(root), DILEMMAS, "date", "outside the allowed window")


def test_an_injury_effect_after_its_own_block_is_accepted(root: Path) -> None:
    edit(
        root,
        DILEMMAS,
        lambda d: d["dilemmas"][5]["options"][0]["effects"][0].update(date=date(2001, 5, 1)),
    )

    load_content_tree(root, release=False)


def test_a_forced_injury_in_the_preseason_is_accepted(root: Path) -> None:
    edit(
        root,
        SEASON_FILE,
        lambda d: d["forced_events"][0].update(date=date(2000, 7, 20), days=30),
    )

    load_content_tree(root, release=False)


@pytest.mark.parametrize("keys", [5, 11])
def test_a_rival_squad_needs_between_6_and_10_key_players(root: Path, keys: int) -> None:
    def mutate(d: dict[str, Any]) -> None:
        for index, player in enumerate(d["players"]):
            player["key"] = index < keys
            if player["key"]:
                player["rating_rationale"] = "Fictional rationale."
            else:
                player.pop("rating_rationale", None)

    edit(root, "club-seasons/mock-city-2000-01/squad.yaml", mutate)

    assert_issue(
        issues_of(root),
        "club-seasons/mock-city-2000-01/squad.yaml",
        "players",
        "between 6 and 10 key players",
    )


# --------------------------------------------------------------------------- branch coverage
def test_the_own_team_cannot_be_its_own_opponent(root: Path) -> None:
    edit(root, FIXTURES, lambda d: fixture_of(d, "tfc-liga-01").update(opponent=OWN))

    assert_issue(issues_of(root), FIXTURES, ".opponent", "own team")


def test_a_league_fixture_with_a_stage_and_no_round_is_reported(root: Path) -> None:
    def mutate(d: dict[str, Any]) -> None:
        fixture = fixture_of(d, "tfc-liga-01")
        fixture.pop("round")
        fixture["stage"] = "final"

    edit(root, FIXTURES, mutate)

    issues = issues_of(root)
    assert_issue(issues, FIXTURES, ".round", "needs a round")
    assert_issue(issues, FIXTURES, ".stage", "no stage or group")


def test_a_league_round_beyond_the_last_is_reported(root: Path) -> None:
    edit(root, FIXTURES, lambda d: fixture_of(d, "tfc-liga-01").update(round=11))

    assert_issue(issues_of(root), FIXTURES, ".round", "beyond the last round")


def test_a_league_match_on_neutral_ground_is_reported(root: Path) -> None:
    edit(root, FIXTURES, lambda d: fixture_of(d, "tfc-liga-01").update(venue="neutral"))

    assert_issue(issues_of(root), FIXTURES, ".venue", "neutral")


def test_a_league_round_played_twice_is_reported(root: Path) -> None:
    edit(root, FIXTURES, lambda d: fixture_of(d, "tfc-liga-02").update(round=1))

    assert_issue(issues_of(root), FIXTURES, "fixtures", "round 1 appears twice")


def test_a_cup_fixture_without_a_stage_is_reported(root: Path) -> None:
    def mutate(d: dict[str, Any]) -> None:
        fixture = fixture_of(d, "tfc-copa-final")
        fixture.pop("stage")
        fixture["round"] = 1

    edit(root, FIXTURES, mutate)

    assert_issue(issues_of(root), FIXTURES, ".stage", "needs a stage")


def test_a_group_fixture_without_a_group_is_reported(root: Path) -> None:
    def mutate(d: dict[str, Any]) -> None:
        fixture = fixture_of(d, "tfc-cont-g1")
        fixture.pop("group")
        fixture.pop("round")

    edit(root, FIXTURES, mutate)

    assert_issue(issues_of(root), FIXTURES, ".group", "unknown group")


def test_a_group_matchday_out_of_range_is_reported(root: Path) -> None:
    edit(root, FIXTURES, lambda d: fixture_of(d, "tfc-cont-g1").update(round=9))

    assert_issue(issues_of(root), FIXTURES, ".round", "matchday")


def test_a_group_match_on_neutral_ground_is_reported(root: Path) -> None:
    edit(root, FIXTURES, lambda d: fixture_of(d, "tfc-cont-g1").update(venue="neutral"))

    assert_issue(issues_of(root), FIXTURES, ".venue", "group match")


def test_a_knockout_fixture_with_a_group_is_reported(root: Path) -> None:
    edit(root, FIXTURES, lambda d: fixture_of(d, "tfc-copa-final").update(group="a"))

    assert_issue(issues_of(root), FIXTURES, ".group", "only group-stage")


def test_a_single_leg_stage_with_leg_two_is_reported(root: Path) -> None:
    edit(root, FIXTURES, lambda d: fixture_of(d, "tfc-copa-final").update(leg=2))

    assert_issue(issues_of(root), FIXTURES, ".leg", "single leg")


def test_a_two_legged_tie_on_neutral_ground_is_reported(root: Path) -> None:
    edit(root, FIXTURES, lambda d: fixture_of(d, "tfc-copa-sf-1").update(venue="neutral"))

    assert_issue(issues_of(root), FIXTURES, ".venue", "two-legged")


def test_a_single_round_robin_league_meets_each_rival_exactly_once(root: Path) -> None:
    def mutate(d: dict[str, Any]) -> None:
        d["competitions"][0]["rounds"] = 1
        d["competitions"][0]["league_stats"]["matches"] = 15

    edit(root, SEASON_FILE, mutate)

    assert_issue(issues_of(root), FIXTURES, "fixtures", "exactly once")


# --- season.yaml
def test_a_market_squad_cannot_take_part_in_a_competition(root: Path) -> None:
    edit(
        root,
        SEASON_FILE,
        lambda d: d["competitions"][1]["participants"].__setitem__(1, "_market-2000-01"),
    )

    assert_issue(issues_of(root), SEASON_FILE, "competitions.1.participants.1", "unknown")


def test_an_outcome_of_an_unknown_competition_is_reported(root: Path) -> None:
    edit(
        root,
        SEASON_FILE,
        lambda d: d["historical_outcome"][1].update(competition="nope"),
    )

    assert_issue(issues_of(root), SEASON_FILE, "historical_outcome.1.competition", "nope")


def test_a_league_outcome_cannot_have_an_elimination_stage(root: Path) -> None:
    edit(
        root,
        SEASON_FILE,
        lambda d: d["historical_outcome"][0].update(eliminated_in="final"),
    )

    assert_issue(issues_of(root), SEASON_FILE, "eliminated_in", "no elimination")


def test_a_cup_outcome_cannot_have_a_final_position(root: Path) -> None:
    edit(root, SEASON_FILE, lambda d: d["historical_outcome"][1].update(final_position=1))

    assert_issue(issues_of(root), SEASON_FILE, "historical_outcome.1.final_position", "leagues")


def test_an_elimination_in_an_unknown_stage_is_reported(root: Path) -> None:
    edit(
        root,
        SEASON_FILE,
        lambda d: d["historical_outcome"][3].update(eliminated_in="nope"),
    )

    assert_issue(issues_of(root), SEASON_FILE, "historical_outcome.3.eliminated_in", "nope")


def test_an_objective_on_an_unknown_competition_is_reported(root: Path) -> None:
    edit(
        root,
        SEASON_FILE,
        lambda d: d["board_objectives"][0].update(competition="nope"),
    )

    assert_issue(issues_of(root), SEASON_FILE, "board_objectives.0.competition", "nope")


def test_outcomes_are_not_contradicted_when_the_real_data_is_incomplete(root: Path) -> None:
    """Without the brackets, group tables or the final league table nothing can be derived."""

    def mutate(d: dict[str, Any]) -> None:
        d["ties"] = []
        d["cutoffs"] = [c for c in d["cutoffs"] if c.get("stage") is None and c["block"] != "b5"]
        d["cutoffs"].append(next(c for c in d["cutoffs"]))  # keep the shape non-trivial

    edit(root, STANDINGS, mutate)
    issues = issues_of(root)

    assert not [i for i in issues if "contradicts" in i.message]


def test_a_pending_tie_winner_cannot_contradict_the_outcome(root: Path) -> None:
    def mutate(d: dict[str, Any]) -> None:
        for tie in d["ties"]:
            tie.update(winner=None, verify="pending")

    edit(root, STANDINGS, mutate)

    load_content_tree(root, release=False)


# --- standings.yaml
def test_a_cutoff_in_an_unknown_block_is_reported(root: Path) -> None:
    edit(root, STANDINGS, lambda d: d["cutoffs"][0].update(block="b9"))

    assert_issue(issues_of(root), STANDINGS, "cutoffs.0.block", "b9")


def test_a_league_cutoff_of_a_cup_is_reported(root: Path) -> None:
    edit(root, STANDINGS, lambda d: d["cutoffs"][0].update(competition="copa-test"))

    assert_issue(issues_of(root), STANDINGS, "cutoffs.0.competition", "not a league")


def test_a_group_cutoff_of_a_knockout_stage_is_reported(root: Path) -> None:
    def mutate(d: dict[str, Any]) -> None:
        group = next(c for c in d["cutoffs"] if c.get("stage") == "groups")
        group["stage"] = "final"

    edit(root, STANDINGS, mutate)

    assert_issue(issues_of(root), STANDINGS, ".stage", "not a group stage")


def test_a_group_cutoff_of_an_unknown_group_is_reported(root: Path) -> None:
    def mutate(d: dict[str, Any]) -> None:
        group = next(c for c in d["cutoffs"] if c.get("stage") == "groups")
        group["group"] = "z"

    edit(root, STANDINGS, mutate)

    assert_issue(issues_of(root), STANDINGS, ".group", "unknown group")


def test_a_wrong_points_total_in_a_group_table_is_reported(root: Path) -> None:
    def mutate(d: dict[str, Any]) -> None:
        group = next(c for c in d["cutoffs"] if c.get("stage") == "groups")
        group["table"][0]["points"] += 0  # keep order valid
        group["table"][-1]["points"] = 0
        group["table"][-1]["won"] = 1
        group["table"][-1]["played"] = group["table"][-1]["won"] + group["table"][-1]["drawn"]
        group["table"][-1]["lost"] = 0

    edit(root, STANDINGS, mutate)

    assert any(i.path == STANDINGS for i in issues_of(root))


def test_a_tie_of_a_league_is_reported(root: Path) -> None:
    edit(root, STANDINGS, lambda d: d["ties"][0].update(competition="liga-test"))

    assert_issue(issues_of(root), STANDINGS, "ties.0.competition", "not a knockout")


def test_a_tie_in_a_group_stage_is_reported(root: Path) -> None:
    def mutate(d: dict[str, Any]) -> None:
        tie = d["ties"][-1]
        tie["stage"] = "groups"

    edit(root, STANDINGS, mutate)

    assert_issue(issues_of(root), STANDINGS, ".stage", "unknown knockout stage")


def test_the_real_league_played_must_match_the_final_table(root: Path) -> None:
    edit(root, SQUAD, lambda d: d["real_league"].update(played=d["real_league"]["played"] + 1))

    assert_issue(issues_of(root), SQUAD, "real_league.played", "standings")


def test_a_dilemma_effect_on_a_squadless_rival_is_reported(root: Path) -> None:
    edit(
        root,
        DILEMMAS,
        lambda d: d["dilemmas"][4]["options"][0]["effects"][0].update(
            to_club_season="placeholder-town-2000-01"
        ),
    )

    assert_issue(issues_of(root), DILEMMAS, "to_club_season", "no squad")


def test_a_dilemma_effect_that_targets_the_own_team_is_reported(root: Path) -> None:
    edit(
        root,
        DILEMMAS,
        lambda d: d["dilemmas"][4]["options"][0]["effects"][0].update(to_club_season=OWN),
    )

    assert_issue(issues_of(root), DILEMMAS, "to_club_season", "own team")


# --- penalties and extra time in two-legged ties and single matches
def _second_leg_level_on_aggregate(data: dict[str, Any]) -> None:
    """sf-1 is 2-1; sf-2 becomes 0-1: 2-2 on aggregate, settled on penalties."""
    fixture_of(data, "tfc-copa-sf-2")["result"] = {
        "goals_for": 0,
        "goals_against": 1,
        "penalties_for": 4,
        "penalties_against": 3,
    }


def test_second_leg_penalties_are_valid_when_the_aggregate_is_level(root: Path) -> None:
    edit(root, FIXTURES, _second_leg_level_on_aggregate)

    load_content_tree(root, release=False)


def test_second_leg_penalties_are_reported_when_the_aggregate_is_not_level(root: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        _second_leg_level_on_aggregate(data)
        fixture_of(data, "tfc-copa-sf-2")["result"]["goals_for"] = 3

    edit(root, FIXTURES, mutate)

    assert_issue(issues_of(root), FIXTURES, "fixtures", "level on aggregate")


def test_first_leg_penalties_are_reported(root: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        fixture_of(data, "tfc-copa-sf-1")["result"] = {
            "goals_for": 1,
            "goals_against": 1,
            "penalties_for": 4,
            "penalties_against": 3,
        }

    edit(root, FIXTURES, mutate)

    assert_issue(issues_of(root), FIXTURES, ".result", "first leg")


def test_single_match_penalties_need_a_level_score(root: Path) -> None:
    edit(
        root,
        FIXTURES,
        lambda d: fixture_of(d, "tfc-copa-final")["result"].update(goals_for=2),
    )

    assert_issue(issues_of(root), FIXTURES, ".result", "level score")
