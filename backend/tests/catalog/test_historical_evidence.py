"""Explicit sourced historical evidence for the synthetic Test FC season."""

import shutil
from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError
from tests.catalog.test_content_tree import FIXTURE_ROOT, OWN, SEASON, assert_issue, edit, issues_of
from tests.contracts.suites.expected_test_fc import build_expected_test_fc_season

from mister.catalog.infrastructure.content_schema import load_content_tree
from mister.catalog.infrastructure.content_schema.evidence import HeadToHeadEvidence
from mister.catalog.infrastructure.content_schema.season import Stage
from mister.catalog.infrastructure.content_schema.standings import RealTie, StandingsFile

SOURCE = "https://example.org/test-content/evidence"
DAY = date(2000, 9, 2)
OTHER = "fixture-wanderers-2000-01"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    target = tmp_path / "content"
    shutil.copytree(FIXTURE_ROOT, target)
    return target


def evidence(**overrides: Any) -> dict[str, Any]:
    return {
        "competition": "liga-test",
        "covered_clubs": [OWN, OTHER],
        "complete_through": DAY,
        "schedule": [],
        "results": [],
        "sources": [SOURCE],
        "verify": "ok",
        **overrides,
    }


def fixture(**overrides: Any) -> dict[str, Any]:
    return {
        "fixture_id": "tfc-liga-01",
        "date": DAY,
        "home": OWN,
        "away": OTHER,
        "sources": [SOURCE],
        "verify": "ok",
        **overrides,
    }


def result(**overrides: Any) -> dict[str, Any]:
    return {
        "fixture_id": "tfc-liga-01",
        "score": [0, 1],
        "sources": [SOURCE],
        "verify": "ok",
        **overrides,
    }


def stage(**overrides: Any) -> dict[str, Any]:
    return {
        "id": "semifinal",
        "name": "Test semifinal",
        "round": "semi_final",
        "legs": 2,
        "away_goals_rule": True,
        "extra_time": True,
        "penalties": True,
        **overrides,
    }


def test_unknown_evidence_is_distinct_from_verified_empty_calendar() -> None:
    unknown = StandingsFile.model_validate({"schema_version": 1, "cutoffs": []})
    known = StandingsFile.model_validate(
        {"schema_version": 1, "cutoffs": [], "head_to_head": [evidence()]}
    )
    assert unknown.head_to_head is None
    assert known.head_to_head is not None
    assert known.head_to_head[0].schedule == ()
    assert known.head_to_head[0].results == ()


def test_cutoff_is_inclusive_and_results_keep_home_away_orientation() -> None:
    parsed = HeadToHeadEvidence.model_validate(evidence(schedule=[fixture()], results=[result()]))
    assert parsed.schedule[0].date == parsed.complete_through
    assert parsed.results[0].score == (0, 1)
    assert str(parsed.schedule[0].sources[0]) == SOURCE


@pytest.mark.parametrize(
    "change",
    [
        {"schedule": [fixture(), fixture()], "results": [result()]},
        {"schedule": [fixture()], "results": [result(), result()]},
        {"schedule": [fixture()], "results": []},
        {"schedule": [], "results": [result()]},
        {"schedule": [fixture(home=OTHER)], "results": [result()]},
        {"schedule": [fixture(away="sample-united-2000-01")], "results": [result()]},
        {"schedule": [fixture(date=DAY + timedelta(days=1))], "results": [result()]},
        {"covered_clubs": [OWN, OWN]},
        {"stage": "groups"},
        {"schedule": [fixture(sources=[])], "results": [result()]},
        {"schedule": [fixture()], "results": [result(score=None)]},
        {"schedule": [fixture()], "results": [result(score=[True, 1])]},
        {"schedule": [fixture()], "results": [result(score=[-1, 1])]},
    ],
)
def test_invalid_evidence_is_rejected_without_coercion(change: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        HeadToHeadEvidence.model_validate(evidence(**change))


def test_missing_score_remains_null_and_pending_in_development(root: Path) -> None:
    def pending(data: dict[str, Any]) -> None:
        data["head_to_head"][0]["results"][0].update(score=None, verify="pending")

    edit(root, f"{SEASON}/standings.yaml", pending)
    load_content_tree(root, release=False)
    assert_issue(issues_of(root, release=True), f"{SEASON}/standings.yaml", "verify", "pending")


def test_release_requires_evidence_for_each_scope_using_direct_criteria(root: Path) -> None:
    edit(root, f"{SEASON}/standings.yaml", lambda d: d.update(head_to_head=None))
    load_content_tree(root, release=False)
    assert_issue(
        issues_of(root, release=True), f"{SEASON}/standings.yaml", "head_to_head", "coverage"
    )


def test_non_direct_criteria_do_not_require_evidence(root: Path) -> None:
    def general(data: dict[str, Any]) -> None:
        for competition in data["competitions"]:
            if competition["kind"] == "league":
                competition["tiebreakers"] = ["goal_difference"]
            for entry in competition.get("stages", []):
                if entry["round"] == "group_stage":
                    entry["tiebreakers"] = ["goal_difference"]

    edit(root, f"{SEASON}/season.yaml", general)
    edit(root, f"{SEASON}/standings.yaml", lambda d: d.update(head_to_head=None))
    load_content_tree(root, release=True)


def test_complete_synthetic_evidence_includes_matches_between_rivals(root: Path) -> None:
    tree = load_content_tree(root, release=True)
    history = tree.seasons[OWN].standings.head_to_head
    assert history is not None
    assert [len(h.schedule) for h in history] == [30, 12]
    assert any(OWN not in (f.home, f.away) for f in history[0].schedule)


@pytest.mark.parametrize(
    ("mutation", "part"),
    [
        (lambda h: h.update(competition="unknown"), "competition"),
        (lambda h: h.update(stage="groups", group="a"), "stage"),
        (lambda h: h.update(covered_clubs=[*h["covered_clubs"], "ghost-2000-01"]), "covered_clubs"),
        (lambda h: h.update(complete_through=date(2002, 1, 1)), "complete_through"),
    ],
)
def test_evidence_scope_and_season_are_validated(root: Path, mutation: Any, part: str) -> None:
    edit(root, f"{SEASON}/standings.yaml", lambda d: mutation(d["head_to_head"][0]))
    assert_issue(issues_of(root), f"{SEASON}/standings.yaml", part)


def test_managed_fixture_score_must_agree_with_evidence(root: Path) -> None:
    def conflict(data: dict[str, Any]) -> None:
        row = next(
            r for r in data["head_to_head"][0]["results"] if r["fixture_id"] == "tfc-liga-01"
        )
        row["score"] = [9, 0]

    edit(root, f"{SEASON}/standings.yaml", conflict)
    assert_issue(issues_of(root), f"{SEASON}/standings.yaml", "head_to_head", "managed fixture")


def test_managed_fixture_cannot_be_omitted_from_covered_calendar(root: Path) -> None:
    def omit(data: dict[str, Any]) -> None:
        h = data["head_to_head"][0]
        for key in ("schedule", "results"):
            h[key] = [x for x in h[key] if x["fixture_id"] != "tfc-liga-01"]

    edit(root, f"{SEASON}/standings.yaml", omit)
    assert_issue(
        issues_of(root), f"{SEASON}/standings.yaml", "head_to_head", "missing managed fixture"
    )


def test_full_coverage_is_compared_with_every_covered_cutoff(root: Path) -> None:
    def conflict(data: dict[str, Any]) -> None:
        h = data["head_to_head"][0]
        foreign = next(f for f in h["schedule"] if OWN not in (f["home"], f["away"]))
        row = next(r for r in h["results"] if r["fixture_id"] == foreign["fixture_id"])
        row["score"][0] += 1

    edit(root, f"{SEASON}/standings.yaml", conflict)
    assert_issue(issues_of(root), f"{SEASON}/standings.yaml", "head_to_head", "table")


def test_overlapping_snapshots_must_not_contradict_each_other(root: Path) -> None:
    def conflict(data: dict[str, Any]) -> None:
        extra = deepcopy(data["head_to_head"][0])
        extra["covered_clubs"] = [OWN, OTHER]
        ids = {f["fixture_id"] for f in extra["schedule"] if {f["home"], f["away"]} == {OWN, OTHER}}
        for key in ("schedule", "results"):
            extra[key] = [f for f in extra[key] if f["fixture_id"] in ids]
        extra["results"][0]["score"] = [8, 0]
        data["head_to_head"].append(extra)

    edit(root, f"{SEASON}/standings.yaml", conflict)
    assert_issue(issues_of(root), f"{SEASON}/standings.yaml", "head_to_head", "contradict")


@pytest.mark.parametrize("value", [True, False])
def test_away_goals_during_extra_time_is_explicit_sourced_and_nullable(value: bool) -> None:
    parsed = Stage.model_validate(
        stage(away_goals_in_extra_time={"value": value, "sources": [SOURCE], "verify": "ok"})
    )
    assert parsed.away_goals_in_extra_time is not None
    assert parsed.away_goals_in_extra_time.value is value
    unknown = Stage.model_validate(
        stage(away_goals_in_extra_time={"value": None, "sources": [], "verify": "pending"})
    )
    assert unknown.away_goals_in_extra_time is not None
    assert unknown.away_goals_in_extra_time.value is None


@pytest.mark.parametrize(
    "rules",
    [{"legs": 1, "away_goals_rule": False}, {"away_goals_rule": False}, {"extra_time": False}],
)
def test_away_goals_in_extra_time_true_is_rejected_when_inapplicable(rules: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        Stage.model_validate(
            stage(
                **rules,
                away_goals_in_extra_time={"value": True, "sources": [SOURCE], "verify": "ok"},
            )
        )


def test_release_requires_explicit_extra_time_rule_when_all_three_conditions_apply(
    root: Path,
) -> None:
    edit(
        root,
        f"{SEASON}/season.yaml",
        lambda d: d["competitions"][1]["stages"][0].update(extra_time=True),
    )
    load_content_tree(root, release=False)
    assert_issue(
        issues_of(root, release=True),
        f"{SEASON}/season.yaml",
        "away_goals_in_extra_time",
        "explicit",
    )


def test_a_real_tie_requires_distinct_clubs() -> None:
    with pytest.raises(ValidationError):
        RealTie.model_validate(
            {
                "competition": "copa-test",
                "stage": "final",
                "clubs": [OWN, OWN],
                "winner": OWN,
                "sources": [SOURCE],
                "verify": "ok",
            }
        )


def test_a_club_cannot_participate_twice_in_the_same_knockout_stage(root: Path) -> None:
    edit(root, f"{SEASON}/standings.yaml", lambda d: d["ties"].append(d["ties"][0].copy()))
    assert_issue(issues_of(root), f"{SEASON}/standings.yaml", "ties", "twice")


def test_a_known_loser_cannot_reappear_in_the_next_connected_stage(root: Path) -> None:
    edit(
        root, f"{SEASON}/standings.yaml", lambda d: d["ties"][1].update(winner="mock-city-2000-01")
    )
    assert_issue(issues_of(root), f"{SEASON}/standings.yaml", "ties", "winner")


def test_a_pending_predecessor_does_not_create_an_invented_lineage(root: Path) -> None:
    edit(
        root,
        f"{SEASON}/standings.yaml",
        lambda d: d["ties"][1].update(winner=None, verify="pending"),
    )
    load_content_tree(root, release=False)


def test_managed_id_cannot_be_reused_for_unrelated_rivals_in_a_partial_scope(root: Path) -> None:
    rivals = ["sample-united-2000-01", "demo-athletic-2000-01"]
    invalid = evidence(
        covered_clubs=rivals, schedule=[fixture(home=rivals[0], away=rivals[1])], results=[result()]
    )
    edit(root, f"{SEASON}/standings.yaml", lambda d: d.update(head_to_head=[invalid]))
    assert_issue(issues_of(root), f"{SEASON}/standings.yaml", "head_to_head", "managed fixture")


def test_a_postponed_match_after_coverage_does_not_make_an_empty_calendar_incomplete(
    root: Path,
) -> None:
    before = evidence(complete_through=DAY - timedelta(days=1))
    edit(root, f"{SEASON}/standings.yaml", lambda d: d.update(head_to_head=[before]))
    load_content_tree(root, release=False)


def test_partial_coverage_at_the_first_cutoff_does_not_satisfy_later_release_cutoffs(
    root: Path,
) -> None:
    def shorten(data: dict[str, Any]) -> None:
        h = data["head_to_head"][0]
        h["complete_through"] = date(2000, 9, 30)
        ids = {f["fixture_id"] for f in h["schedule"] if f["date"] <= h["complete_through"]}
        for key in ("schedule", "results"):
            h[key] = [f for f in h[key] if f["fixture_id"] in ids]

    edit(root, f"{SEASON}/standings.yaml", shorten)
    load_content_tree(root, release=False)
    issues = issues_of(root, release=True)
    assert_issue(issues, f"{SEASON}/standings.yaml", "head_to_head", "b2")
    assert not any("coverage" in i.message and "/b1" in i.message for i in issues)


@pytest.mark.parametrize("scope", ["calendar", "result", "coverage"])
def test_each_layer_of_pending_evidence_is_blocked_for_release(root: Path, scope: str) -> None:
    def pending(data: dict[str, Any]) -> None:
        h = data["head_to_head"][0]
        target = (
            h if scope == "coverage" else h["schedule" if scope == "calendar" else "results"][0]
        )
        target["verify"] = "pending"

    edit(root, f"{SEASON}/standings.yaml", pending)
    load_content_tree(root, release=False)
    assert_issue(issues_of(root, release=True), f"{SEASON}/standings.yaml", "verify", "pending")


@pytest.mark.parametrize("value", [True, False])
def test_verified_extra_time_variant_can_ship_and_reaches_the_catalog_oracle(
    root: Path, value: bool
) -> None:
    def explicit(data: dict[str, Any]) -> None:
        data["competitions"][1]["stages"][0].update(
            extra_time=True,
            away_goals_in_extra_time={"value": value, "sources": [SOURCE], "verify": "ok"},
        )

    edit(root, f"{SEASON}/season.yaml", explicit)
    tree = load_content_tree(root, release=True)
    actual = build_expected_test_fc_season(tree)
    assert actual.competitions[1].stages[0].away_goals_in_extra_time is value


@pytest.mark.parametrize(
    ("value", "verify", "sources"), [(None, "pending", []), (False, "pending", [SOURCE])]
)
def test_unverified_extra_time_variant_is_not_release_ready(
    root: Path, value: Any, verify: str, sources: list[str]
) -> None:
    def pending(data: dict[str, Any]) -> None:
        data["competitions"][1]["stages"][0].update(
            extra_time=True,
            away_goals_in_extra_time={"value": value, "sources": sources, "verify": verify},
        )

    edit(root, f"{SEASON}/season.yaml", pending)
    load_content_tree(root, release=False)
    assert_issue(
        issues_of(root, release=True),
        f"{SEASON}/season.yaml",
        "away_goals_in_extra_time",
        "explicit",
    )


def test_duplicate_coverage_declarations_are_rejected(root: Path) -> None:
    edit(
        root,
        f"{SEASON}/standings.yaml",
        lambda d: d["head_to_head"].append(deepcopy(d["head_to_head"][0])),
    )
    assert_issue(issues_of(root), f"{SEASON}/standings.yaml", "head_to_head", "duplicate coverage")


def test_overlapping_calendars_cannot_disagree_by_omitting_a_rival_match(root: Path) -> None:
    def omit(data: dict[str, Any]) -> None:
        extra = deepcopy(data["head_to_head"][0])
        foreign = next(f for f in extra["schedule"] if OWN not in (f["home"], f["away"]))
        extra["covered_clubs"] = [foreign["home"], foreign["away"]]
        extra["schedule"] = []
        extra["results"] = []
        data["head_to_head"].append(extra)

    edit(root, f"{SEASON}/standings.yaml", omit)
    assert_issue(issues_of(root), f"{SEASON}/standings.yaml", "head_to_head", "contradict")


def test_unknown_predecessor_ties_stay_unresolved_instead_of_being_fabricated(root: Path) -> None:
    edit(
        root,
        f"{SEASON}/standings.yaml",
        lambda d: d.update(ties=[t for i, t in enumerate(d["ties"]) if i != 1]),
    )
    load_content_tree(root, release=False)


@pytest.mark.parametrize("release", [False, True])
def test_disjoint_coverage_cannot_reuse_one_fixture_id_for_different_matches(root: Path, release: bool) -> None:
    def general(data: dict[str, Any]) -> None:
        for competition in data["competitions"]:
            if competition["kind"] == "league":
                competition["tiebreakers"] = ["goal_difference"]
            for entry in competition.get("stages", []):
                if entry["round"] == "group_stage":
                    entry["tiebreakers"] = ["goal_difference"]
    edit(root, f"{SEASON}/season.yaml", general)
    first_clubs = ["sample-united-2000-01", "demo-athletic-2000-01"]
    second_clubs = ["mock-city-2000-01", "dummy-rovers-2000-01"]
    histories = []
    for clubs, score in ((first_clubs, [1, 0]), (second_clubs, [0, 2])):
        histories.append(evidence(covered_clubs=clubs, schedule=[fixture(fixture_id="shared-match", home=clubs[0], away=clubs[1])], results=[result(fixture_id="shared-match", score=score)]))
    edit(root, f"{SEASON}/standings.yaml", lambda d: d.update(head_to_head=histories))
    assert_issue(issues_of(root, release=release), f"{SEASON}/standings.yaml", "head_to_head", "fixture id")


@pytest.mark.parametrize("change", [{"competition": "copa-continental-test", "stage": "groups", "group": "a"}, {"date": DAY+timedelta(days=1)}, {"score": [2, 0]}])
def test_shared_fixture_ids_preserve_scope_date_and_non_null_score(root: Path, change: dict[str, Any]) -> None:
    clubs = ["sample-united-2000-01", "demo-athletic-2000-01"]
    first = evidence(covered_clubs=clubs, schedule=[fixture(fixture_id="shared-match", home=clubs[0], away=clubs[1])], results=[result(fixture_id="shared-match", score=[1, 0])])
    second = deepcopy(first)
    second["complete_through"] += timedelta(days=1)
    if "competition" in change:
        second.update(change)
        second["covered_clubs"] = ["overseas-fc-2000-01", "abroad-athletic-2000-01"]
        second["schedule"][0].update(home=second["covered_clubs"][0], away=second["covered_clubs"][1])
    elif "date" in change:
        second["schedule"][0]["date"] = change["date"]
    else:
        second["results"][0]["score"] = change["score"]
    edit(root, f"{SEASON}/standings.yaml", lambda d: d.update(head_to_head=[first, second]))
    assert_issue(issues_of(root), f"{SEASON}/standings.yaml", "head_to_head")


def test_consistent_shared_fixture_ids_can_enrich_a_pending_score(root: Path) -> None:
    clubs = ["sample-united-2000-01", "demo-athletic-2000-01"]
    first = evidence(covered_clubs=clubs, schedule=[fixture(fixture_id="shared-match", home=clubs[0], away=clubs[1])], results=[result(fixture_id="shared-match", score=None, verify="pending")])
    second = deepcopy(first)
    second["complete_through"] += timedelta(days=1)
    second["results"][0].update(score=[1, 0], verify="ok")
    edit(root, f"{SEASON}/standings.yaml", lambda d: d.update(head_to_head=[first, second]))
    load_content_tree(root, release=False)
