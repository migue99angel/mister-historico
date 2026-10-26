"""Block orchestration with fictional teams and deterministic pure strategies."""

from dataclasses import replace
from datetime import date

import pytest

from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import BlockId, ClubSeasonId, CompetitionId, FixtureId, PlayerId
from mister.shared_kernel.randomness import StdlibRandomSource
from mister.shared_kernel.seed import Seed
from mister.simulation.application.api import (
    AggregateTeamInput,
    BlockSimRequest,
    BlockSummaryDTO,
    CompetitionInput,
    FixtureInput,
    ForcedInjuryDTO,
    RealResultInput,
    SeasonSimInput,
    SimulationService,
    SquadPlayerInput,
    SquadTeamInput,
    StandingRowDTO,
    StandingsDTO,
    TacticDTO,
)
from mister.simulation.domain.model import MatchResult, MatchSetup, Score

ME = ClubSeasonId("test-fc-2000-01")
RIVAL = ClubSeasonId("sample-united-2000-01")
LEAGUE = CompetitionId("liga-test")
START = date(2000, 9, 1)
END = date(2000, 9, 3)


def team() -> SquadTeamInput:
    positions = ("GK", "GK", *("DF",) * 6, *("MF",) * 6, *("FW",) * 4)
    return SquadTeamInput(
        ME,
        tuple(
            SquadPlayerInput(PlayerId(f"test-{i:02}"), position, 70 + i % 5)
            for i, position in enumerate(positions)
        ),
        TacticDTO("balanced", "4-4-2"),
    )  # type: ignore[arg-type]


def request() -> BlockSimRequest:
    fixtures = tuple(
        FixtureInput(
            FixtureId(f"test-{i}"),
            date(2000, 9, i),
            LEAGUE,
            ME if i == 1 else RIVAL,
            RIVAL if i == 1 else ME,
            key=i == 1,
            round=i,
            real_result=RealResultInput(1, 0),
        )
        for i in (1, 3)
    )
    snapshots = tuple(
        StandingsDTO(
            LEAGUE,
            day,
            (
                StandingRowDTO(ME, 1, n, n, 0, 0, n, 0, 3 * n),
                StandingRowDTO(RIVAL, 2, n, 0, 0, n, 0, n, 0),
            ),
        )
        for day, n in ((START, 1), (END, 2))
    )
    season = SeasonSimInput(
        ME,
        (team(), AggregateTeamInput(RIVAL, 70, 70)),
        (
            CompetitionInput(
                LEAGUE,
                "league",
                "domestic_league",
                (ME, RIVAL),
                1.2,
                1.15,
                rounds=2,
                points_per_win=3,
                points_per_draw=1,
                tiebreakers=("goal_difference", "goals_for"),
            ),
        ),
        fixtures,
        historical_standings=snapshots,
    )
    return BlockSimRequest(season, BlockId("test-block"), START, END, team())


class FixedMatches:
    """Fake strategy retaining setups to observe physical and tactical inputs."""

    def __init__(self, score: Score = Score(1, 0)) -> None:
        self.score = score
        self.setups: list[MatchSetup] = []

    def simulate(self, setup: MatchSetup, rng: object, *, decisive: bool = False) -> MatchResult:
        self.setups.append(setup)
        return MatchResult(self.score)

    def extra_time(self, setup: MatchSetup, rng: object) -> Score:
        return Score(0, 0)

    def penalty_shootout(self, setup: MatchSetup, rng: object) -> Score:
        return Score(4, 3)


def play(value: BlockSimRequest, fake: FixedMatches | None = None) -> BlockSummaryDTO:
    from mister.simulation.application.simulate_block import _simulate

    return _simulate(value, StdlibRandomSource(Seed(1)), fake or FixedMatches())


def continuation(original: BlockSimRequest, summary: BlockSummaryDTO) -> BlockSimRequest:
    states = {state.player_id: state for state in summary.player_states}
    return replace(
        original,
        start=date(2000, 9, 2),
        state_as_of=START,
        prior_results=summary.results,
        managed_team=replace(
            original.managed_team,
            players=tuple(
                replace(
                    p,
                    fitness=states[p.player_id].fitness,
                    injured_until=states[p.player_id].injured_until,
                )
                for p in original.managed_team.players
            ),
        ),
    )


def test_only_block_fixtures_are_played_with_inclusive_boundaries() -> None:
    summary = play(replace(request(), end=START))
    assert tuple(r.fixture_id for r in summary.results) == (FixtureId("test-1"),)
    assert summary.key_matches == (FixtureId("test-1"),)


def test_fixtures_are_processed_in_date_and_identifier_order() -> None:
    value = request()
    summary = play(
        replace(value, season=replace(value.season, fixtures=value.season.fixtures[::-1]))
    )
    assert tuple(r.date for r in summary.results) == (START, END)


def test_seeded_replay_is_exact_and_preserves_input() -> None:
    value = request()
    assert SimulationService().simulate_block(value, StdlibRandomSource(Seed(5))) == (
        SimulationService().simulate_block(value, StdlibRandomSource(Seed(5)))
    )
    assert all(p.fitness == 100 for p in value.managed_team.players)


def test_split_blocks_preserve_scores_and_physical_state() -> None:
    value = request()
    first = play(replace(value, end=START))
    second = play(continuation(value, first))
    whole = play(value)
    assert (*first.results, *second.results) == whole.results
    assert tuple((p.fitness, p.injured_until) for p in second.player_states) == tuple(
        (p.fitness, p.injured_until) for p in whole.player_states
    )
    assert second.standings == whole.standings
    assert sum(p.minutes_played for p in second.player_states) == 11 * 90


def test_empty_block_recovers_until_its_exact_close() -> None:
    value = request()
    players = tuple(replace(p, fitness=40) for p in value.managed_team.players)
    summary = play(
        replace(
            value,
            start=date(2000, 9, 4),
            end=date(2000, 9, 6),
            state_as_of=END,
            prior_results=play(value).results,
            managed_team=replace(value.managed_team, players=players),
        )
    )
    assert summary.results == ()
    assert all(p.fitness == 52 and p.minutes_played == 0 for p in summary.player_states)


def test_youth_player_gets_minutes_without_altering_rating() -> None:
    value = request()
    youth = replace(value.managed_team.players[-1], rating=1, youth_minutes=True)
    players = (*value.managed_team.players[:-1], youth)
    summary = play(replace(value, managed_team=replace(value.managed_team, players=players)))
    assert (
        next(p for p in summary.player_states if p.player_id == youth.player_id).minutes_played > 0
    )
    assert youth.rating == 1


def test_forced_injury_precedes_selection_and_return_is_available_on_exact_date() -> None:
    value = request()
    injured = value.managed_team.players[0].player_id
    summary = play(
        replace(value, forced_injuries_from_effects=(ForcedInjuryDTO(injured, START, 2),))
    )
    assert summary.injuries[0].forced
    assert next(p for p in summary.player_states if p.player_id == injured).injured_until is None


def test_initial_absence_does_not_invent_a_forced_injury_event() -> None:
    value = request()
    players = (
        replace(value.managed_team.players[0], injured_until=END),
        *value.managed_team.players[1:],
    )
    summary = play(replace(value, managed_team=replace(value.managed_team, players=players)))
    assert all(i.player_id != players[0].player_id for i in summary.injuries)


def test_prior_results_are_replaced_against_original_p2_snapshot() -> None:
    value = request()
    first = play(replace(value, end=START), FixedMatches(Score(0, 1)))
    second = play(continuation(value, first), FixedMatches(Score(1, 0)))
    rows = {r.club_season_id: r for r in second.standings[0].rows}
    assert rows[ME].points == 0
    assert rows[RIVAL].points == 6


@pytest.mark.parametrize(
    "change",
    [
        {"start": date(2000, 10, 1)},
        {"state_as_of": date(2000, 9, 2)},
        {"team_morale": 101},
        {"competition_priorities": {CompetitionId("unknown"): "high"}},
        {"competition_priorities": {LEAGUE: "invalid"}},
    ],
)
def test_invalid_block_inputs_are_rejected(change: dict[str, object]) -> None:
    with pytest.raises(InvalidValueError):
        play(replace(request(), **change))  # type: ignore[arg-type]


def test_a_missing_fixture_in_a_continuation_gap_is_rejected() -> None:
    with pytest.raises(InvalidValueError, match="prior|missing|gap"):
        play(replace(request(), start=date(2000, 9, 2)))


def test_duplicate_prior_results_are_rejected() -> None:
    value = request()
    first = play(replace(value, end=START))
    with pytest.raises(InvalidValueError):
        play(replace(continuation(value, first), prior_results=first.results * 2))


def test_future_prior_results_are_rejected() -> None:
    value = request()
    with pytest.raises(InvalidValueError):
        play(replace(value, prior_results=play(value).results))


@pytest.mark.parametrize("field,bad", [("morale", 101), ("fitness", -1), ("rating", 100)])
@pytest.mark.parametrize("source", ["reference", "override"])
def test_neutral_rival_inputs_are_validated_before_state_is_normalized(
    field: str, bad: int, source: str,
) -> None:
    value = request()
    rival = replace(team(), club_season_id=RIVAL)
    bad_player = replace(rival.players[0], **{field: bad})
    rival = replace(rival, players=(bad_player, *rival.players[1:]))
    if source == "reference":
        value = replace(value, season=replace(value.season, teams=(team(), rival)))
    else:
        value = replace(value, team_overrides=(rival,))
    with pytest.raises(InvalidValueError):
        play(value)


def test_rival_injury_is_projected_at_match_date_without_changing_reference() -> None:
    value = request()
    rival = replace(team(), club_season_id=RIVAL)
    star = replace(rival.players[-1], rating=99)
    rival = replace(rival, players=(*rival.players[:-1], star))
    healthy_fake = FixedMatches()
    injured_fake = FixedMatches()
    play(replace(value, team_overrides=(rival,)), healthy_fake)
    injured = replace(star, injured_until=END)
    play(replace(value, team_overrides=(replace(rival, players=(*rival.players[:-1], injured)),)),
         injured_fake)
    assert injured_fake.setups[0].away.attack < healthy_fake.setups[0].away.attack
    assert injured_fake.setups[1].home.attack == healthy_fake.setups[1].home.attack


def test_duplicate_forced_injury_from_content_and_effect_is_emitted_once() -> None:
    value = request()
    injury = ForcedInjuryDTO(value.managed_team.players[0].player_id, START, 2)
    value = replace(value, season=replace(value.season, forced_injuries=(injury,)),
                    forced_injuries_from_effects=(injury,))
    summary = play(value)
    assert len(tuple(i for i in summary.injuries if i.forced)) == 1


def test_prior_league_match_cannot_contain_extra_time_or_penalties() -> None:
    value = request()
    first = play(replace(value, end=START), FixedMatches(Score(0, 0)))
    invalid = replace(first.results[0], extra_time=(0, 0), penalties=(4, 3),
                      winner="home", user_result="win")
    with pytest.raises(InvalidValueError):
        play(replace(continuation(value, first), prior_results=(invalid,)))


def test_team_override_is_measured_against_the_original_strength_reference() -> None:
    value = request()
    old = FixedMatches()
    better = FixedMatches()
    play(value, old)
    rival = replace(team(), club_season_id=RIVAL,
                    players=tuple(replace(p, rating=99) for p in team().players))
    play(replace(value, team_overrides=(rival,)), better)
    assert old.setups[0].home == better.setups[0].home
    assert old.setups[0].away.attack < better.setups[0].away.attack
    assert old.setups[0].away.defense > better.setups[0].away.defense


def test_full_test_fc_season_matches_five_continuations_including_injuries_and_events() -> None:
    from tests.simulation.unit.benchmark_season import test_fc_request

    value = test_fc_request()
    whole = SimulationService().simulate_block(value, StdlibRandomSource(Seed(20261026)))
    periods = ((date(2000, 8, 1), date(2000, 9, 30)),
               (date(2000, 10, 1), date(2000, 11, 30)),
               (date(2000, 12, 1), date(2001, 1, 31)),
               (date(2001, 2, 1), date(2001, 3, 31)),
               (date(2001, 4, 1), date(2001, 5, 31)))
    summaries = []
    prior = ()
    managed = value.managed_team
    cursor = None
    for start, end in periods:
        summary = SimulationService().simulate_block(replace(value, start=start, end=end,
            managed_team=managed, state_as_of=cursor, prior_results=prior),
            StdlibRandomSource(Seed(20261026)))
        summaries.append(summary)
        prior = (*prior, *summary.results)
        states = {p.player_id: p for p in summary.player_states}
        managed = replace(managed, players=tuple(replace(p, fitness=states[p.player_id].fitness,
            injured_until=states[p.player_id].injured_until) for p in managed.players))
        cursor = end
    assert prior == whole.results
    assert tuple(e for s in summaries for e in s.events) == whole.events
    assert tuple(i for s in summaries for i in s.injuries) == whole.injuries
    assert summaries[-1].standings == whole.standings
    assert tuple((p.player_id, p.fitness, p.injured_until) for p in summaries[-1].player_states) == tuple(
        (p.player_id, p.fitness, p.injured_until) for p in whole.player_states)
