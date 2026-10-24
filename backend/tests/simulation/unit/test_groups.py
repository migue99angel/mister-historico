"""Four synthetic clubs and explicit evidence, without third-party simulation."""

from dataclasses import replace
from datetime import date

import pytest

from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import ClubSeasonId, CompetitionId, FixtureId
from mister.simulation.domain.groups import GroupEvidence, GroupMatch, GroupRules, GroupTable
from mister.simulation.domain.league_types import LeagueRow
from mister.simulation.domain.model import FixtureSpec, Score

CLUBS = tuple(ClubSeasonId(f"{club}-2000-01") for club in ("test-fc", "demo-athletic", "sample-united", "dummy-rovers"))
CUTOFF = date(2001, 2, 1)


def _row(club: ClubSeasonId, *, gf: int = 0, ga: int = 0, wins: int = 0) -> LeagueRow:
    return LeagueRow(club, 3, wins, 3 - wins, 0, gf, ga, wins * 3 + 3 - wins)


def _rules(*criteria: str, reapply: bool = False) -> GroupRules:
    return GroupRules(3, 1, criteria, 2, reapply_head_to_head=reapply)


def _match(home: int, away: int, score: tuple[int, int]) -> GroupMatch:
    return GroupMatch(FixtureSpec(FixtureId(f"group-{home}-{away}"), date(2001, 1, 1), CompetitionId("test-champions"), CLUBS[home], CLUBS[away], stage="groups", group="a"), Score(*score))


def _evidence(*matches: GroupMatch) -> GroupEvidence:
    return GroupEvidence(CUTOFF, tuple(m.fixture for m in matches), matches)


def _table(rules: GroupRules, *, evidence: GroupEvidence | None = None, rows: tuple[LeagueRow, ...] | None = None) -> GroupTable:
    return GroupTable(CompetitionId("test-champions"), "groups", "a", CLUBS, rows or tuple(_row(club) for club in CLUBS), rules, evidence)


@pytest.mark.parametrize(("criterion", "rows"), [
    ("goal_difference", tuple(_row(c, gf=i) for i, c in enumerate(CLUBS))),
    ("goals_for", tuple(_row(c, gf=i, ga=i) for i, c in enumerate(CLUBS))),
    ("wins", tuple(_row(c, wins=i) for i, c in enumerate(CLUBS))),
])
def test_group_orders_by_configured_overall_criteria(criterion: str, rows: tuple[LeagueRow, ...]) -> None:
    ranking = _table(_rules(criterion), rows=rows).rank()
    assert tuple(row.club_season_id for row in ranking.rows) == CLUBS[::-1]
    assert ranking.qualifiers == CLUBS[::-1][:2]


@pytest.mark.parametrize("criterion", ["head_to_head_points", "head_to_head_goal_difference", "head_to_head_goals_for", "head_to_head_away_goals"])
def test_head_to_head_criteria_use_only_explicit_mini_table_matches(criterion: str) -> None:
    rows = tuple(_row(c, gf=20 if c == CLUBS[0] else 0) for c in CLUBS)
    ranking = _table(_rules(criterion, "goals_for"), rows=rows, evidence=_evidence(_match(0, 1, (0, 2)))).rank()
    assert ranking.rows[0].club_season_id == CLUBS[1]


def test_unknown_head_to_head_evidence_fails_instead_of_inventing_scores() -> None:
    with pytest.raises(InvalidValueError, match="evidence"):
        _table(_rules("head_to_head_points")).rank()


def test_known_empty_evidence_produces_zeroes_and_an_unresolved_stable_order() -> None:
    ranking = _table(_rules("head_to_head_points"), evidence=_evidence()).rank()
    assert tuple(r.club_season_id for r in ranking.rows) == tuple(sorted(CLUBS, key=str))
    assert ranking.unresolved_ties == (tuple(sorted(CLUBS, key=str)),)
    with pytest.raises(InvalidValueError, match="unresolved"):
        _ = ranking.qualifiers


def test_missing_required_scheduled_result_fails() -> None:
    match = _match(0, 1, (2, 0))
    evidence = GroupEvidence(CUTOFF, (match.fixture,), ())
    with pytest.raises(InvalidValueError, match="missing"):
        _table(_rules("head_to_head_points"), evidence=evidence).rank()


def test_future_scheduled_results_are_not_required() -> None:
    match = _match(0, 1, (2, 0))
    evidence = GroupEvidence(date(2000, 12, 31), (match.fixture,), ())
    assert _table(_rules("head_to_head_points"), evidence=evidence).rank().unresolved_ties


def test_no_head_to_head_evidence_is_required_after_points_resolve_order() -> None:
    rows = tuple(_row(c, wins=i) for i, c in enumerate(CLUBS))
    assert not _table(_rules("head_to_head_points"), rows=rows).rank().unresolved_ties


def test_mini_table_reapplication_is_an_explicit_synthetic_rule() -> None:
    # A/B/C have 3 H2H points. A scores 4, B/C score 2; reapplying ranks B above C.
    matches = (_match(0, 1, (4, 0)), _match(1, 2, (2, 0)), _match(2, 0, (2, 0)))
    rows = tuple(_row(c, gf=9 if i == 2 else 0, wins=1 if i < 3 else 0) for i, c in enumerate(CLUBS))
    criteria = ("head_to_head_points", "head_to_head_goals_for", "goals_for")
    without = _table(_rules(*criteria), rows=rows, evidence=_evidence(*matches)).rank()
    with_reapply = _table(_rules(*criteria, reapply=True), rows=rows, evidence=_evidence(*matches)).rank()
    assert tuple(r.club_season_id for r in without.rows)[:3] == (CLUBS[0], CLUBS[2], CLUBS[1])
    assert tuple(r.club_season_id for r in with_reapply.rows)[:3] == CLUBS[:3]


def test_group_rejects_evidence_for_another_group() -> None:
    match = _match(0, 1, (2, 0))
    wrong = replace(match, fixture=replace(match.fixture, group="b"))
    with pytest.raises(InvalidValueError, match="group"):
        _table(_rules("head_to_head_points"), evidence=_evidence(wrong))


def test_group_requires_four_distinct_rows() -> None:
    with pytest.raises(InvalidValueError):
        replace(_table(_rules("goal_difference")), participants=CLUBS[:3])
