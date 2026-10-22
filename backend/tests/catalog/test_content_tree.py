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
    assert len(tree.clubs) == 7


def test_the_synthetic_test_fc_tree_passes_release_validation(root: Path) -> None:
    tree = load_content_tree(root, release=True)

    assert set(tree.squads) >= {OWN, "_market-2000-01"}
    assert set(tree.aggregates) == {"placeholder-town-2000-01"}


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
    edit(root, SQUAD, lambda d: d.update(real_goals_for=d["real_goals_for"] + 1))

    assert_issue(issues_of(root), SQUAD, "real_goals_for", "standings")


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
    edit(root, f"{SEASON}/season.yaml", lambda d: d["historical_outcome"].pop())

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
