"""Checks of `fixtures.yaml` against the season: competitions, stages, groups, legs and dates."""

from collections import Counter, defaultdict
from itertools import pairwise
from typing import TYPE_CHECKING

from mister.catalog.infrastructure.content_schema.context import SeasonContext, stage_of
from mister.catalog.infrastructure.content_schema.fixtures import Fixture
from mister.catalog.infrastructure.content_schema.season import (
    Competition,
    LeagueCompetition,
    Stage,
)

if TYPE_CHECKING:
    from datetime import date

TWO_LEGS = 2


def check_fixtures(ctx: SeasonContext) -> None:
    """Report every inconsistency between the own fixtures and the season definition."""
    for index, fixture in enumerate(ctx.content.fixtures.fixtures):
        field = f"fixtures.{index}"
        competition = ctx.competitions.get(fixture.competition)
        if competition is None:
            ctx.add(
                "fixtures",
                f"{field}.competition",
                f"unknown competition {fixture.competition!r}",
            )
            continue
        _check_opponent(ctx, field, fixture.opponent, competition)
        if ctx.block_of(fixture.date) is None:
            ctx.add("fixtures", f"{field}.date", f"{fixture.date} falls outside every block")
        _check_shape(ctx, field, fixture, competition)
        _check_penalties(ctx, field, fixture)
    for competition in ctx.content.season.competitions:
        if isinstance(competition, LeagueCompetition):
            _check_league_completeness(ctx, competition)
        else:
            _check_group_completeness(ctx, competition)
            _check_legs(ctx, competition)
            _check_stage_order(ctx, competition)


def _check_penalties(ctx: SeasonContext, field: str, fixture: Fixture) -> None:
    """A shoot-out follows a level single match; in a second leg it follows a level aggregate
    (checked with the whole tie in `_check_two_legs`); a first leg never has one."""
    result = fixture.result
    if result is None or result.penalties_for is None:
        return
    if fixture.leg == 1:
        ctx.add("fixtures", f"{field}.result", "a first leg cannot go to penalties")
    elif fixture.leg is None and result.goals_for != result.goals_against:
        ctx.add("fixtures", f"{field}.result", "penalties need a level score")


def _check_opponent(
    ctx: SeasonContext, field: str, opponent: str, competition: Competition
) -> None:
    if not ctx.exists(opponent):
        ctx.add("fixtures", f"{field}.opponent", f"unknown club-season {opponent!r}")
    elif opponent == ctx.own:
        ctx.add("fixtures", f"{field}.opponent", "the opponent cannot be the own team")
    elif opponent not in competition.participants:
        ctx.add(
            "fixtures",
            f"{field}.opponent",
            f"{opponent!r} is not a participant of {competition.id!r}",
        )


def _check_shape(
    ctx: SeasonContext, field: str, fixture: Fixture, competition: Competition
) -> None:
    if isinstance(competition, LeagueCompetition):
        _check_league_fixture(ctx, field, fixture, competition)
        return
    if fixture.stage is None:
        ctx.add("fixtures", f"{field}.stage", "a fixture of this competition needs a stage")
        return
    stage = stage_of(competition, fixture.stage)
    if stage is None:
        ctx.add("fixtures", f"{field}.stage", f"unknown stage {fixture.stage!r}")
    elif stage.is_group_stage:
        _check_group_fixture(ctx, field, fixture, stage)
    else:
        _check_knockout_fixture(ctx, field, fixture, stage)


def _check_league_fixture(
    ctx: SeasonContext, field: str, fixture: Fixture, competition: LeagueCompetition
) -> None:
    last_round = (len(competition.participants) - 1) * competition.rounds
    if fixture.round is None:
        ctx.add("fixtures", f"{field}.round", "a league fixture needs a round")
    elif fixture.round > last_round:
        ctx.add("fixtures", f"{field}.round", f"round {fixture.round} is beyond the last round")
    if fixture.stage is not None or fixture.group is not None:
        ctx.add("fixtures", f"{field}.stage", "a league fixture has no stage or group")
    if fixture.venue == "neutral":
        ctx.add("fixtures", f"{field}.venue", "a league match is never on neutral ground")


def _check_group_fixture(ctx: SeasonContext, field: str, fixture: Fixture, stage: Stage) -> None:
    group = next((g for g in stage.groups or () if g.id == fixture.group), None)
    if group is None:
        ctx.add("fixtures", f"{field}.group", f"unknown group {fixture.group!r} in {stage.id!r}")
        return
    if ctx.own not in group.participants:
        ctx.add("fixtures", f"{field}.group", f"the own team is not in group {group.id!r}")
    if fixture.opponent not in group.participants:
        ctx.add(
            "fixtures",
            f"{field}.opponent",
            f"{fixture.opponent!r} is not in group {group.id!r}",
        )
    last = (len(group.participants) - 1) * stage.legs
    if fixture.round is None or not 1 <= fixture.round <= last:
        ctx.add("fixtures", f"{field}.round", f"the matchday must be between 1 and {last}")


def _check_knockout_fixture(ctx: SeasonContext, field: str, fixture: Fixture, stage: Stage) -> None:
    if fixture.group is not None or fixture.round is not None:
        ctx.add("fixtures", f"{field}.group", "only group-stage fixtures have a group or round")
    if stage.legs == TWO_LEGS:
        if fixture.leg is None:
            ctx.add(
                "fixtures", f"{field}.leg", f"stage {stage.id!r} is two-legged: leg is required"
            )
        if fixture.venue == "neutral":
            ctx.add("fixtures", f"{field}.venue", "a two-legged tie is never on neutral ground")
    elif fixture.leg not in (None, 1):
        ctx.add("fixtures", f"{field}.leg", f"stage {stage.id!r} has a single leg")


def _own_fixtures(ctx: SeasonContext, competition_id: str) -> list[Fixture]:
    return [f for f in ctx.content.fixtures.fixtures if f.competition == competition_id]


def _check_league_completeness(ctx: SeasonContext, competition: LeagueCompetition) -> None:
    own = _own_fixtures(ctx, competition.id)
    expected = (len(competition.participants) - 1) * competition.rounds
    if len(own) != expected:
        ctx.add(
            "fixtures",
            "fixtures",
            f"{competition.id}: expected {expected} fixtures of the own team, found {len(own)}",
        )
    _check_unique_rounds(ctx, competition.id, own)
    for opponent in competition.participants:
        if opponent != ctx.own:
            _check_pair(ctx, competition.id, opponent, own, competition.rounds)


def _check_unique_rounds(ctx: SeasonContext, label: str, fixtures: list[Fixture]) -> None:
    rounds = Counter(f.round for f in fixtures if f.round is not None)
    for number, count in rounds.items():
        if count > 1:
            ctx.add("fixtures", "fixtures", f"{label}: round {number} appears twice")


def _check_pair(
    ctx: SeasonContext, label: str, opponent: str, fixtures: list[Fixture], legs: int
) -> None:
    venues = sorted(f.venue for f in fixtures if f.opponent == opponent)
    if legs == TWO_LEGS:
        valid, what = venues == ["away", "home"], "once at home and once away"
    else:
        valid, what = len(venues) == 1, "exactly once"
    if not valid:
        ctx.add("fixtures", "fixtures", f"{label}: {opponent} must be met {what}")


def _check_group_completeness(ctx: SeasonContext, competition: Competition) -> None:
    if isinstance(competition, LeagueCompetition):
        return
    for stage in competition.stages:
        for group in stage.groups or ():
            if ctx.own not in group.participants:
                continue
            own = [
                f
                for f in _own_fixtures(ctx, competition.id)
                if f.stage == stage.id and f.group == group.id
            ]
            label = f"{competition.id}/{stage.id}/{group.id}"
            expected = (len(group.participants) - 1) * stage.legs
            if len(own) != expected:
                ctx.add(
                    "fixtures",
                    "fixtures",
                    f"{label}: expected {expected} fixtures of the own team, found {len(own)}",
                )
            _check_unique_rounds(ctx, label, own)
            for opponent in group.participants:
                if opponent != ctx.own:
                    pair = [f for f in own if f.opponent == opponent]
                    if any(f.venue == "neutral" for f in pair):
                        if len(pair) != stage.legs:
                            ctx.add(
                                "fixtures",
                                "fixtures",
                                f"{label}: each opponent needs {stage.legs} matches",
                            )
                    else:
                        _check_pair(ctx, label, opponent, own, stage.legs)


def _check_legs(ctx: SeasonContext, competition: Competition) -> None:
    if isinstance(competition, LeagueCompetition):
        return
    for stage in competition.stages:
        if stage.is_group_stage or stage.legs != TWO_LEGS:
            continue
        legs_by_opponent: dict[str, list[int]] = defaultdict(list)
        for fixture in _own_fixtures(ctx, competition.id):
            if fixture.stage == stage.id and fixture.leg is not None:
                legs_by_opponent[fixture.opponent].append(fixture.leg)
        for opponent, legs in legs_by_opponent.items():
            label = f"{competition.id}/{stage.id}: {opponent}"
            if sorted(legs) == [1, 2]:
                _check_two_legs(ctx, label, competition.id, stage.id, opponent)
                continue
            if len(set(legs)) < len(legs):
                ctx.add("fixtures", "fixtures", f"{label} has two fixtures for the same leg")
            elif legs == [1]:
                ctx.add("fixtures", "fixtures", f"{label} has only the first leg")
            else:
                ctx.add("fixtures", "fixtures", f"{label} has only the second leg")


def _check_two_legs(
    ctx: SeasonContext, label: str, competition_id: str, stage_id: str, opponent: str
) -> None:
    ties = {
        f.leg: f
        for f in _own_fixtures(ctx, competition_id)
        if f.stage == stage_id and f.opponent == opponent
    }
    if sorted(f.venue for f in ties.values()) != ["away", "home"]:
        ctx.add("fixtures", "fixtures", f"{label} needs one leg at home and the other away")
    if ties[1].date >= ties[2].date:
        ctx.add("fixtures", "fixtures", f"{label}: leg 1 must be played before leg 2")
    first, second = ties[1].result, ties[2].result
    if first is not None and second is not None and second.penalties_for is not None:
        goals_for = first.goals_for + second.goals_for
        goals_against = first.goals_against + second.goals_against
        if goals_for != goals_against:
            ctx.add(
                "fixtures",
                "fixtures",
                f"{label}: penalties in the second leg need the tie level on aggregate",
            )


def _check_stage_order(ctx: SeasonContext, competition: Competition) -> None:
    if isinstance(competition, LeagueCompetition):
        return
    dates: list[tuple[str, date, date]] = []
    for stage in competition.stages:
        days = [f.date for f in _own_fixtures(ctx, competition.id) if f.stage == stage.id]
        if days:
            dates.append((stage.id, min(days), max(days)))
    for (earlier, _, earlier_end), (later, later_start, _) in pairwise(dates):
        if later_start <= earlier_end:
            ctx.add(
                "fixtures",
                "fixtures",
                f"{competition.id}: stage {later!r} starts before stage {earlier!r} ends",
            )
