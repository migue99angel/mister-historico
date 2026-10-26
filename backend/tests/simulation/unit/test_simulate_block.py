"""Block orchestration with fictional teams and deterministic pure strategies."""

from dataclasses import replace
from datetime import date

import pytest

from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import BlockId, ClubSeasonId, CompetitionId, FixtureId, PlayerId
from mister.shared_kernel.randomness import StdlibRandomSource
from mister.shared_kernel.seed import Seed
from mister.simulation.application.api import (
    AggregateTeamInput, BlockSimRequest, BlockSummaryDTO, CompetitionInput, FixtureInput,
    ForcedInjuryDTO, RealResultInput, SeasonSimInput, SimulationService, SquadPlayerInput,
    SquadTeamInput, StandingRowDTO, StandingsDTO, TacticDTO,
)
from mister.simulation.domain.model import MatchResult, MatchSetup, Score

ME = ClubSeasonId("test-fc-2000-01")
RIVAL = ClubSeasonId("sample-united-2000-01")
LEAGUE = CompetitionId("liga-test")
START = date(2000, 9, 1)
END = date(2000, 9, 3)


def team() -> SquadTeamInput:
    positions = ("GK", "GK", *("DF",) * 6, *("MF",) * 6, *("FW",) * 4)
    return SquadTeamInput(ME, tuple(
        SquadPlayerInput(PlayerId(f"test-{i:02}"), position, 70 + i % 5)
        for i, position in enumerate(positions)
    ), TacticDTO("balanced", "4-4-2"))  # type: ignore[arg-type]


def request() -> BlockSimRequest:
    fixtures = tuple(FixtureInput(
        FixtureId(f"test-{i}"), date(2000, 9, i), LEAGUE,
        ME if i == 1 else RIVAL, RIVAL if i == 1 else ME,
        key=i == 1, round=i, real_result=RealResultInput(1, 0),
    ) for i in (1, 3))
    snapshots = tuple(StandingsDTO(LEAGUE, day, (
        StandingRowDTO(ME, 1, n, n, 0, 0, n, 0, 3*n),
        StandingRowDTO(RIVAL, 2, n, 0, 0, n, 0, n, 0),
    )) for day, n in ((START, 1), (END, 2)))
    season = SeasonSimInput(ME, (team(), AggregateTeamInput(RIVAL, 70, 70)), (
        CompetitionInput(LEAGUE, "league", "domestic_league", (ME, RIVAL), 1.2, 1.15,
                         rounds=2, points_per_win=3, points_per_draw=1,
                         tiebreakers=("goal_difference", "goals_for")),
    ), fixtures, historical_standings=snapshots)
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
    return replace(original, start=date(2000, 9, 2), state_as_of=START,
                   prior_results=summary.results, managed_team=replace(original.managed_team,
                   players=tuple(replace(p, fitness=states[p.player_id].fitness,
                   injured_until=states[p.player_id].injured_until)
                   for p in original.managed_team.players)))


def test_only_block_fixtures_are_played_with_inclusive_boundaries() -> None:
    summary = play(replace(request(), end=START))
    assert tuple(r.fixture_id for r in summary.results) == (FixtureId("test-1"),)
    assert summary.key_matches == (FixtureId("test-1"),)


def test_fixtures_are_processed_in_date_and_identifier_order() -> None:
    value = request()
    summary = play(replace(value, season=replace(value.season, fixtures=value.season.fixtures[::-1])))
    assert tuple(r.date for r in summary.results) == (START, END)


def test_seeded_replay_is_exact_and_preserves_input() -> None:
    value = request()
    assert SimulationService().simulate_block(value, StdlibRandomSource(Seed(5))) == (
        SimulationService().simulate_block(value, StdlibRandomSource(Seed(5))))
    assert all(p.fitness == 100 for p in value.managed_team.players)


def test_split_blocks_preserve_scores_and_physical_state() -> None:
    value = request()
    first = play(replace(value, end=START))
    second = play(continuation(value, first))
    whole = play(value)
    assert (*first.results, *second.results) == whole.results
    assert tuple((p.fitness, p.injured_until) for p in second.player_states) == tuple(
        (p.fitness, p.injured_until) for p in whole.player_states)
    assert second.standings == whole.standings
    assert sum(p.minutes_played for p in second.player_states) == 11 * 90


def test_empty_block_recovers_until_its_exact_close() -> None:
    value = request()
    players = tuple(replace(p, fitness=40) for p in value.managed_team.players)
    summary = play(replace(value, start=date(2000, 9, 4), end=date(2000, 9, 6),
                          state_as_of=END, prior_results=play(value).results,
                          managed_team=replace(value.managed_team, players=players)))
    assert summary.results == ()
    assert all(p.fitness == 52 and p.minutes_played == 0 for p in summary.player_states)


def test_youth_player_gets_minutes_without_altering_rating() -> None:
    value = request()
    youth = replace(value.managed_team.players[-1], rating=1, youth_minutes=True)
    players = (*value.managed_team.players[:-1], youth)
    summary = play(replace(value, managed_team=replace(value.managed_team, players=players)))
    assert next(p for p in summary.player_states if p.player_id == youth.player_id).minutes_played > 0
    assert youth.rating == 1


def test_forced_injury_precedes_selection_and_return_is_available_on_exact_date() -> None:
    value = request()
    injured = value.managed_team.players[0].player_id
    summary = play(replace(value, forced_injuries_from_effects=(ForcedInjuryDTO(injured, START, 2),)))
    assert summary.injuries[0].forced
    assert next(p for p in summary.player_states if p.player_id == injured).injured_until is None


def test_initial_absence_does_not_invent_a_forced_injury_event() -> None:
    value = request()
    players = (replace(value.managed_team.players[0], injured_until=END), *value.managed_team.players[1:])
    summary = play(replace(value, managed_team=replace(value.managed_team, players=players)))
    assert all(i.player_id != players[0].player_id for i in summary.injuries)


def test_prior_results_are_replaced_against_original_p2_snapshot() -> None:
    value = request()
    first = play(replace(value, end=START), FixedMatches(Score(0, 1)))
    second = play(continuation(value, first), FixedMatches(Score(1, 0)))
    rows = {r.club_season_id: r for r in second.standings[0].rows}
    assert rows[ME].points == 0
    assert rows[RIVAL].points == 6


@pytest.mark.parametrize("change", [
    {"start": date(2000, 10, 1)}, {"state_as_of": date(2000, 9, 2)}, {"team_morale": 101},
    {"competition_priorities": {CompetitionId("unknown"): "high"}},
    {"competition_priorities": {LEAGUE: "invalid"}},
])
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
