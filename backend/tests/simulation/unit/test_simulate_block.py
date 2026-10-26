"""Block orchestration with fictional teams and deterministic pure strategies."""

from dataclasses import replace
from datetime import date

import pytest
from tests.simulation.unit.benchmark_season import build_test_fc_request

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
    MatchResultDTO,
    PositionName,
    RealResultInput,
    SeasonSimInput,
    SimulationService,
    SquadPlayerInput,
    SquadTeamInput,
    StandingRowDTO,
    StandingsDTO,
    TacticDTO,
)
from mister.simulation.application.simulate_block import _map_request, _simulate
from mister.simulation.domain.lineup import select_lineup
from mister.simulation.domain.model import MatchResult, MatchSetup, Score
from mister.simulation.domain.strength import StrengthReference, calculate_strength

ME = ClubSeasonId("test-fc-2000-01")
RIVAL = ClubSeasonId("sample-united-2000-01")
LEAGUE = CompetitionId("liga-test")
START = date(2000, 9, 1)
END = date(2000, 9, 3)


def team() -> SquadTeamInput:
    positions: tuple[PositionName, ...] = ("GK", "GK", *("DF",) * 6, *("MF",) * 6, *("FW",) * 4)
    return SquadTeamInput(
        ME,
        tuple(
            SquadPlayerInput(PlayerId(f"test-{i:02}"), position, 70 + i % 5)
            for i, position in enumerate(positions)
        ),
        TacticDTO("balanced", "4-4-2"),
    )


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

    def __init__(self, score: Score | None = None) -> None:
        self.score = Score(1, 0) if score is None else score
        self.setups: list[MatchSetup] = []

    def simulate(self, setup: MatchSetup, rng: object, *, decisive: bool = False) -> MatchResult:
        self.setups.append(setup)
        return MatchResult(self.score)

    def extra_time(self, setup: MatchSetup, rng: object) -> Score:
        return Score(0, 0)

    def penalty_shootout(self, setup: MatchSetup, rng: object) -> Score:
        return Score(4, 3)


def play(value: BlockSimRequest, fake: FixedMatches | None = None) -> BlockSummaryDTO:
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
    with pytest.raises(InvalidValueError, match=r"prior|missing|gap"):
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


@pytest.mark.parametrize(("field", "bad"), [("morale", 101), ("fitness", -1), ("rating", 100)])
@pytest.mark.parametrize("source", ["reference", "override"])
def test_neutral_rival_inputs_are_validated_before_state_is_normalized(
    field: str,
    bad: int,
    source: str,
) -> None:
    value = request()
    rival = replace(team(), club_season_id=RIVAL)
    bad_player = (
        replace(rival.players[0], morale=bad)
        if field == "morale"
        else replace(rival.players[0], fitness=bad)
        if field == "fitness"
        else replace(rival.players[0], rating=bad)
    )
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
    play(
        replace(value, team_overrides=(replace(rival, players=(*rival.players[:-1], injured)),)),
        injured_fake,
    )
    assert injured_fake.setups[0].away.attack < healthy_fake.setups[0].away.attack
    assert injured_fake.setups[1].home.attack == healthy_fake.setups[1].home.attack


def test_duplicate_forced_injury_from_content_and_effect_is_emitted_once() -> None:
    value = request()
    injury = ForcedInjuryDTO(value.managed_team.players[0].player_id, START, 2)
    value = replace(
        value,
        season=replace(value.season, forced_injuries=(injury,)),
        forced_injuries_from_effects=(injury,),
    )
    summary = play(value)
    assert len(tuple(i for i in summary.injuries if i.forced)) == 1


def test_prior_league_match_cannot_contain_extra_time_or_penalties() -> None:
    value = request()
    first = play(replace(value, end=START), FixedMatches(Score(0, 0)))
    invalid = replace(
        first.results[0], extra_time=(0, 0), penalties=(4, 3), winner="home", user_result="win"
    )
    with pytest.raises(InvalidValueError):
        play(replace(continuation(value, first), prior_results=(invalid,)))


def test_team_override_is_measured_against_the_original_strength_reference() -> None:
    value = request()
    old = FixedMatches()
    better = FixedMatches()
    play(value, old)
    rival = replace(
        team(), club_season_id=RIVAL, players=tuple(replace(p, rating=99) for p in team().players)
    )
    play(replace(value, team_overrides=(rival,)), better)
    assert old.setups[0].home == better.setups[0].home
    assert old.setups[0].away.attack < better.setups[0].away.attack
    assert old.setups[0].away.defense > better.setups[0].away.defense


def test_full_test_fc_season_matches_five_continuations_including_injuries_and_events() -> None:
    value = build_test_fc_request()
    whole = SimulationService().simulate_block(value, StdlibRandomSource(Seed(20261026)))
    periods = (
        (date(2000, 8, 1), date(2000, 9, 30)),
        (date(2000, 10, 1), date(2000, 11, 30)),
        (date(2000, 12, 1), date(2001, 1, 31)),
        (date(2001, 2, 1), date(2001, 3, 31)),
        (date(2001, 4, 1), date(2001, 5, 31)),
    )
    summaries = []
    prior: tuple[MatchResultDTO, ...] = ()
    managed = value.managed_team
    cursor = None
    for start, end in periods:
        summary = SimulationService().simulate_block(
            replace(
                value,
                start=start,
                end=end,
                managed_team=managed,
                state_as_of=cursor,
                prior_results=prior,
            ),
            StdlibRandomSource(Seed(20261026)),
        )
        summaries.append(summary)
        prior = (*prior, *summary.results)
        states = {p.player_id: p for p in summary.player_states}
        managed = replace(
            managed,
            players=tuple(
                replace(
                    p,
                    fitness=states[p.player_id].fitness,
                    injured_until=states[p.player_id].injured_until,
                )
                for p in managed.players
            ),
        )
        cursor = end
    assert prior == whole.results
    assert tuple(e for s in summaries for e in s.events) == whole.events
    assert tuple(i for s in summaries for i in s.injuries) == whole.injuries
    assert summaries[-1].standings == whole.standings
    assert tuple(
        (p.player_id, p.fitness, p.injured_until) for p in summaries[-1].player_states
    ) == tuple((p.player_id, p.fitness, p.injured_until) for p in whole.player_states)


class ManagedWins(FixedMatches):
    def simulate(self, setup: MatchSetup, rng: object, *, decisive: bool = False) -> MatchResult:
        return MatchResult(Score(1, 0) if setup.fixture.home == ME else Score(0, 1))


def test_league_champion_is_emitted_at_evidenced_completion_and_never_repeated() -> None:
    value = request()
    whole = play(value, ManagedWins())
    assert tuple(
        (event.kind, event.date, event.competition_id, event.stage_id) for event in whole.events
    ) == (("champion", END, LEAGUE, None),)
    first = play(replace(value, end=START), ManagedWins())
    assert first.events == ()
    last = play(
        replace(
            value,
            start=date(2000, 9, 4),
            end=date(2000, 9, 5),
            prior_results=whole.results,
            state_as_of=END,
        )
    )
    assert last.events == ()


def test_unresolved_original_rival_tie_is_preserved_in_the_adjusted_table() -> None:
    value = request()
    third = ClubSeasonId("demo-athletic-2000-01")
    competition = replace(value.season.competitions[0], participants=(ME, RIVAL, third), rounds=1)
    fixtures = (
        FixtureInput(
            FixtureId("first"), START, LEAGUE, ME, RIVAL, real_result=RealResultInput(0, 1)
        ),
        FixtureInput(FixtureId("last"), END, LEAGUE, ME, third, real_result=RealResultInput(0, 1)),
    )
    snapshot = StandingsDTO(
        LEAGUE,
        END,
        (
            StandingRowDTO(RIVAL, 1, 2, 1, 1, 0, 1, 0, 4),
            StandingRowDTO(third, 2, 2, 1, 1, 0, 1, 0, 4),
            StandingRowDTO(ME, 3, 2, 0, 0, 2, 0, 2, 0),
        ),
        unresolved_ties=((RIVAL, third),),
    )
    value = replace(
        value,
        season=replace(
            value.season,
            competitions=(competition,),
            fixtures=fixtures,
            teams=(*value.season.teams, AggregateTeamInput(third, 65, 65)),
            historical_standings=(snapshot,),
        ),
    )
    summary = play(value, FixedMatches(Score(0, 1)))
    assert summary.standings[0].unresolved_ties == ((RIVAL, third),)


@pytest.mark.parametrize("unresolved", [None, ()])
def test_original_snapshot_preserves_unknown_and_known_empty_unresolved_metadata(
    unresolved: tuple[tuple[ClubSeasonId, ...], ...] | None,
) -> None:
    value = request()
    snapshots = tuple(
        replace(s, unresolved_ties=unresolved) for s in value.season.historical_standings
    )
    block = _map_request(
        replace(value, season=replace(value.season, historical_standings=snapshots))
    )
    assert block.snapshots[0].unresolved_ties is unresolved


def test_independent_live_squads_cannot_mutate_an_existing_request_or_summary() -> None:
    value = request()
    before = request()
    first = SimulationService().simulate_block(value, StdlibRandomSource(Seed(15)))
    changed = replace(
        value,
        managed_team=replace(
            value.managed_team,
            players=tuple(replace(p, fitness=40, morale=80) for p in value.managed_team.players),
        ),
    )
    SimulationService().simulate_block(changed, StdlibRandomSource(Seed(15)))
    assert value == before
    assert first == SimulationService().simulate_block(value, StdlibRandomSource(Seed(15)))


def many_youth_request() -> BlockSimRequest:
    value = request()
    players = tuple(
        replace(p, youth_minutes=i < 12) for i, p in enumerate(value.managed_team.players)
    )
    return replace(value, managed_team=replace(value.managed_team, players=players))


def test_twelve_available_youth_players_receive_minutes_across_two_matches() -> None:
    value = many_youth_request()
    fake = FixedMatches()
    summary = play(value, fake)
    states = {p.player_id: p for p in summary.player_states}
    assert all(
        states[p.player_id].minutes_played >= 90
        for p in value.managed_team.players
        if p.youth_minutes
    )
    assert sum(p.minutes_played for p in summary.player_states) == 11 * 180
    block = _map_request(value)
    assert block.managed_team.squad is not None
    assert block.managed_team.tactic is not None
    required = frozenset(p.player_id for p in value.managed_team.players[:11])
    lineup = select_lineup(block.managed_team.squad, block.managed_team.tactic, required=required)
    strength = calculate_strength(
        block.managed_team, StrengthReference.from_teams(block.references), lineup=lineup
    )
    assert fake.setups[0].home == strength
    assert all(
        p.rating == original.rating
        for p, original in zip(value.managed_team.players, team().players, strict=True)
    )


def test_twelve_available_youth_players_cannot_fit_in_one_match() -> None:
    with pytest.raises(InvalidValueError, match=r"youth|required|eleven"):
        play(replace(many_youth_request(), end=START))


def test_known_future_absence_prioritizes_youth_who_can_only_play_the_first_match() -> None:
    value = many_youth_request()
    youth = value.managed_team.players[11]
    injury = ForcedInjuryDTO(youth.player_id, END, 7)
    value = replace(value, forced_injuries_from_effects=(injury,))
    summary = play(value)
    states = {state.player_id: state for state in summary.player_states}
    assert all(states[player.player_id].minutes_played >= 90
               for player in value.managed_team.players if player.youth_minutes)
    assert states[youth.player_id].minutes_played == 90
    assert states[youth.player_id].injured_until == date(2000, 9, 10)
    assert summary.injuries[-1].forced
