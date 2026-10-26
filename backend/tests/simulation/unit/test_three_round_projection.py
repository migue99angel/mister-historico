"""Independent three-round P2 oracles with stable historical representatives."""

from dataclasses import replace
from datetime import date

from tests.simulation.unit.test_season_competitions import SOURCES, OwnWins
from tests.simulation.unit.test_simulate_block import ME, RIVAL, continuation, play, request, team

from mister.shared_kernel.ids import ClubSeasonId, CompetitionId, FixtureId
from mister.simulation.application import api


def three_rounds() -> api.BlockSimRequest:
    clubs = (
        ME,
        RIVAL,
        *(
            ClubSeasonId(f"{club}-2000-01")
            for club in (
                "mock-city",
                "demo-athletic",
                "dummy-rovers",
                "fixture-wanderers",
                "faraway-city",
                "abroad-athletic",
            )
        ),
    )
    a, b, c, d, e, f, g, h = clubs
    competition = CompetitionId("three-round-test")
    pairs = (
        ("quarter", a, b, b, 3),
        ("quarter", c, d, d, 3),
        ("quarter", e, f, e, 3),
        ("quarter", g, h, g, 3),
        ("semi", b, d, d, 6),
        ("semi", e, g, g, 6),
        ("final", d, g, g, 9),
    )
    stages = (
        api.StageInput("quarter", "quarter_final", 1, False, True, True),
        api.StageInput("semi", "semi_final", 1, False, True, True),
        api.StageInput("final", "final", 1, False, True, True),
    )
    ties = tuple(
        api.RealTieInput(stage, (home, away), winner) for stage, home, away, winner, _ in pairs
    )
    slots = tuple(
        api.KnockoutSlotInput(
            FixtureId(f"three-{i}"),
            stage,
            date(2000, 9, day),
            home,
            away,
            "neutral",
            None,
            SOURCES,
            "ok",
        )
        for i, (stage, home, away, _, day) in enumerate(pairs)
    )
    comp = api.CompetitionInput(
        competition, "cup", "domestic_cup", clubs, 1.2, 1.1, stages=stages, real_ties=ties
    )
    own = api.FixtureInput(
        slots[0].fixture_id,
        date(2000, 9, 3),
        competition,
        a,
        b,
        venue="neutral",
        stage_id="quarter",
        real_result=api.RealResultInput(0, 1),
    )
    season = api.SeasonSimInput(
        ME,
        (team(), *(api.AggregateTeamInput(club, 65, 65) for club in clubs[1:])),
        (comp,),
        (own,),
        knockout_calendar=(api.KnockoutCalendarInput(competition, slots, SOURCES, "ok"),),
    )
    return replace(request(), season=season, end=date(2000, 9, 9))


def test_three_round_representatives_move_without_duplicating_the_managed_club() -> None:
    fake = OwnWins()
    summary = play(three_rounds(), fake)
    assert tuple(r.fixture_id for r in summary.results) == tuple(
        FixtureId(f"three-{i}") for i in (0, 4, 6)
    )
    assert tuple(r.opponent.value for r in summary.results) == (
        "sample-united-2000-01",
        "demo-athletic-2000-01",
        "faraway-city-2000-01",
    )
    assert len(fake.setups) == 3
    assert all(r.home != r.away for r in summary.results)
    assert tuple(e.kind for e in summary.events) == ("advanced", "advanced", "champion")


def test_three_blocks_reconstruct_every_previous_effective_historical_representative() -> None:
    value = three_rounds()
    whole = play(value, OwnWins())
    first = play(replace(value, end=date(2000, 9, 3)), OwnWins())
    next_value = replace(
        continuation(value, first), start=date(2000, 9, 4), state_as_of=date(2000, 9, 3)
    )
    second = play(replace(next_value, end=date(2000, 9, 6)), OwnWins())
    last_value = replace(
        continuation(value, second),
        start=date(2000, 9, 7),
        state_as_of=date(2000, 9, 6),
        prior_results=(*first.results, *second.results),
    )
    last = play(last_value, OwnWins())
    assert (*first.results, *second.results, *last.results) == whole.results
    assert (*first.events, *second.events, *last.events) == whole.events
    assert tuple((p.fitness, p.injured_until) for p in last.player_states) == tuple(
        (p.fitness, p.injured_until) for p in whole.player_states
    )
