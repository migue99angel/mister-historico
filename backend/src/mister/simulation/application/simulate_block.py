"""Validate published DTOs and translate to the private pure season coordinator."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, cast

from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import BlockId, ClubSeasonId, CompetitionId, FixtureId, PlayerId
from mister.simulation.domain.injuries import Injury
from mister.simulation.domain.league_types import LeagueRow
from mister.simulation.domain.match_simulator import PoissonMatchSimulator
from mister.simulation.domain.model import (
    AggregateIndices,
    CompetitionParams,
    Fitness,
    FixtureSpec,
    MatchResult,
    Morale,
    Position,
    Priority,
    Rating,
    Score,
    SimPlayer,
    SimTeam,
    Style,
    Tactic,
    Venue,
)
from mister.simulation.domain.season import (
    Block,
    Competition,
    PlayedMatch,
    SeasonFixture,
    SeasonSimulation,
    TableSnapshot,
)

if TYPE_CHECKING:
    from mister.shared_kernel.randomness import RandomSource
    from mister.simulation.application.api import (
        BlockSimRequest,
        BlockSummaryDTO,
        MatchResultDTO,
        TeamInput,
    )
    from mister.simulation.domain.ports import MatchSimulator


def _date(value: date) -> date:
    if type(value) is not date:
        raise InvalidValueError("a calendar date is required")
    return value


def _unique(values: tuple[object, ...], name: str) -> None:
    if len(values) != len(set(values)):
        raise InvalidValueError(f"duplicate {name}")


def _team(value: TeamInput, *, morale: int = 50, neutral: bool = False) -> SimTeam:
    from mister.simulation.application.api import AggregateTeamInput, SquadTeamInput

    if not isinstance(value.club_season_id, ClubSeasonId):
        raise InvalidValueError("team needs a typed club ID")
    if isinstance(value, AggregateTeamInput):
        return SimTeam(
            value.club_season_id, aggregate=AggregateIndices(value.attack, value.defense)
        )
    if not isinstance(value, SquadTeamInput):
        raise InvalidValueError("a squad or aggregate team is required")
    for p in value.players:
        if not isinstance(p.player_id, PlayerId) or type(p.youth_minutes) is not bool:
            raise InvalidValueError("player ID and youth flag must be typed")
        if p.injured_until is not None:
            _date(p.injured_until)
    return SimTeam(
        value.club_season_id,
        squad=tuple(
            SimPlayer(
                p.player_id,
                Position(p.position),
                Rating(p.rating),
                Morale(50 if neutral else p.morale),
                Fitness(100 if neutral else p.fitness),
                False,
                p.age,
            )
            for p in value.players
        ),
        tactic=Tactic(Style(value.tactic.style), value.tactic.system),
        morale=Morale(morale),
    )


def _fixture(value: object) -> SeasonFixture:
    from mister.simulation.application.api import FixtureInput

    if not isinstance(value, FixtureInput):
        raise InvalidValueError("a fixture input is required")
    if not isinstance(value.fixture_id, FixtureId) or not isinstance(
        value.competition_id, CompetitionId
    ):
        raise InvalidValueError("fixtures need typed IDs")
    if not isinstance(value.home, ClubSeasonId) or not isinstance(value.away, ClubSeasonId):
        raise InvalidValueError("fixture sides need typed club IDs")
    if type(value.key) is not bool or (
        value.round is not None and (type(value.round) is not int or value.round <= 0)
    ):
        raise InvalidValueError("invalid key flag or matchday")
    historical = None
    if value.real_result is not None:
        real = value.real_result
        historical = Score(real.goals_for, real.goals_against)
    return SeasonFixture(
        FixtureSpec(
            value.fixture_id,
            _date(value.date),
            value.competition_id,
            value.home,
            value.away,
            Venue(value.venue),
            value.key,
            value.leg,
            value.stage_id,
            value.group_id,
        ),
        value.round,
        historical,
    )


def _record(value: MatchResultDTO, fixture: SeasonFixture, managed: ClubSeasonId) -> PlayedMatch:
    from mister.simulation.application.api import MatchResultDTO

    if not isinstance(value, MatchResultDTO):
        raise InvalidValueError("a prior result needs a typed match report")
    result = MatchResult(
        Score(*value.regulation),
        Score(*value.extra_time) if value.extra_time is not None else None,
        Score(*value.penalties) if value.penalties is not None else None,
    )
    record = PlayedMatch(fixture, result)
    if _report(record, managed) != value:
        raise InvalidValueError("prior result contradicts its effective fixture or outcome")
    return record


def _map_request(value: BlockSimRequest) -> Block:
    from mister.simulation.application.api import SquadTeamInput

    season = value.season
    if not isinstance(value.block_id, BlockId):
        raise InvalidValueError("block needs a typed ID")
    start, end = _date(value.start), _date(value.end)
    state_as_of = start if value.state_as_of is None else _date(value.state_as_of)
    if end < start or state_as_of > start:
        raise InvalidValueError("invalid block range or state date")
    if not isinstance(value.managed_team, SquadTeamInput) or (
        value.managed_team.club_season_id != season.managed_club_season_id
    ):
        raise InvalidValueError("managed squad must identify the season's managed club")
    references = tuple(_team(t, neutral=True) for t in season.teams)
    _unique(tuple(t.club_season_id for t in references), "reference teams")
    team_ids = {t.club_season_id for t in references}
    if season.managed_club_season_id not in team_ids:
        raise InvalidValueError("managed club needs an original reference squad")
    competitions = []
    for c in season.competitions:
        if not isinstance(c.competition_id, CompetitionId) or c.kind not in (
            "league",
            "cup",
            "super_cup",
            "continental_cup",
        ):
            raise InvalidValueError("invalid competition ID or kind")
        _unique(c.participants, "competition participants")
        if (
            len(c.participants) < 2
            or not set(c.participants) <= team_ids
            or (season.managed_club_season_id not in c.participants)
        ):
            raise InvalidValueError("invalid competition participants")
        if c.kind == "league" and (type(c.rounds) is not int or c.rounds not in (1, 2)):
            raise InvalidValueError("a league needs one or two rounds")
        ppw, ppd = c.points_per_win, c.points_per_draw
        if c.kind == "league" and (type(ppw) is not int or type(ppd) is not int):
            raise InvalidValueError("a league needs explicit points rules")
        competitions.append(
            Competition(
                c.competition_id,
                c.kind,
                c.participants,
                CompetitionParams(c.base_goals, c.home_advantage),
                c.rounds,
                ppw if ppw is not None else 0,
                ppd if ppd is not None else 0,
                c.tiebreakers,
            )
        )
    _unique(tuple(c.competition_id for c in competitions), "competitions")
    competition_ids = {c.competition_id for c in competitions}
    priorities = {}
    for competition_id, priority in value.competition_priorities.items():
        if competition_id not in competition_ids:
            raise InvalidValueError("priority refers to an unknown competition")
        priorities[competition_id] = Priority(priority)
    fixtures = tuple(_fixture(f) for f in season.fixtures)
    _unique(tuple(f.spec.fixture_id for f in fixtures), "fixtures")
    competition_map = {c.competition_id: c for c in competitions}
    for fixture in fixtures:
        spec = fixture.spec
        c = competition_map.get(spec.competition_id)
        if (
            c is None
            or not {spec.home, spec.away} <= set(c.participants)
            or (season.managed_club_season_id not in (spec.home, spec.away))
        ):
            raise InvalidValueError("fixture must belong to managed team and its competition")
        if fixture.historical is not None and spec.away == season.managed_club_season_id:
            # Content scores are relative to the managed club, not the nominal home side.
            pass
    fixtures = tuple(
        SeasonFixture(
            f.spec,
            f.round,
            (
                Score(f.historical.away, f.historical.home)
                if f.spec.away == season.managed_club_season_id and f.historical is not None
                else f.historical
            ),
        )
        for f in fixtures
    )
    rivals = tuple(_team(t, neutral=True) for t in value.team_overrides)
    _unique(tuple(t.club_season_id for t in rivals), "team overrides")
    if any(
        t.club_season_id not in team_ids or t.club_season_id == season.managed_club_season_id
        for t in rivals
    ):
        raise InvalidValueError("override needs a known rival")
    fixture_map = {f.spec.fixture_id: f for f in fixtures}
    _unique(tuple(r.fixture_id for r in value.prior_results), "prior results")
    prior = []
    for result in value.prior_results:
        fixture = fixture_map.get(result.fixture_id)
        if fixture is None or result.date >= start:
            raise InvalidValueError("prior result must identify an earlier scheduled fixture")
        prior.append(_record(result, fixture, season.managed_club_season_id))
    snapshots = []
    for snapshot in season.historical_standings:
        if snapshot.competition_id not in competition_ids:
            raise InvalidValueError("table belongs to unknown competition")
        rows = tuple(
            LeagueRow(
                r.club_season_id,
                r.played,
                r.won,
                r.drawn,
                r.lost,
                r.goals_for,
                r.goals_against,
                r.points,
            )
            for r in snapshot.rows
        )
        snapshots.append(
            TableSnapshot(
                snapshot.competition_id,
                _date(snapshot.as_of),
                rows,
                tuple(r.club_season_id for r in sorted(snapshot.rows, key=lambda r: r.position)),
                snapshot.stage_id,
                snapshot.group_id,
            )
        )
    _unique(
        tuple((s.competition_id, s.as_of, s.stage_id, s.group_id) for s in snapshots), "snapshots"
    )
    injuries = tuple(
        Injury(i.player_id, _date(i.date), i.days, True)
        for i in (*season.forced_injuries, *value.forced_injuries_from_effects)
    )
    squad_ids = {p.player_id for p in value.managed_team.players}
    if any(i.player_id not in squad_ids for i in injuries):
        raise InvalidValueError("forced injury refers to a player outside managed squad")
    return Block(
        start,
        end,
        state_as_of,
        _team(value.managed_team, morale=value.team_morale),
        references,
        rivals,
        tuple(competitions),
        fixtures,
        tuple(snapshots),
        (),
        priorities,
        injuries,
        {
            p.player_id: p.injured_until
            for p in value.managed_team.players
            if p.injured_until is not None
        },
        frozenset(p.player_id for p in value.managed_team.players if p.youth_minutes),
        tuple(prior),
    )


def _report(played: PlayedMatch, managed: ClubSeasonId) -> MatchResultDTO:
    from mister.simulation.application.api import MatchResultDTO

    fixture, result = played.fixture, played.result
    spec = fixture.spec
    winner = result.winner
    own_home = spec.home == managed
    user_result = (
        "draw" if winner is None else ("win" if (winner.value == "home") == own_home else "loss")
    )
    return MatchResultDTO(
        spec.fixture_id,
        spec.competition_id,
        spec.date,
        spec.home,
        spec.away,
        (result.regulation.home, result.regulation.away),
        cast(
            "VenueName",
            "neutral" if spec.venue is Venue.NEUTRAL else "home" if own_home else "away",
        ),
        spec.away if own_home else spec.home,
        cast("UserResultName", user_result),
        (result.extra_time.home, result.extra_time.away) if result.extra_time is not None else None,
        (result.penalties.home, result.penalties.away) if result.penalties is not None else None,
        winner.value if winner is not None else None,
        spec.key,
        fixture.round,
        spec.stage,
        spec.group,
        spec.leg,
    )


if TYPE_CHECKING:
    from mister.simulation.application.api import TeamVenueName as VenueName
    from mister.simulation.application.api import UserResultName


def _simulate(
    request: BlockSimRequest, rng: RandomSource, simulator: MatchSimulator
) -> BlockSummaryDTO:
    from mister.simulation.application.api import (
        BlockSummaryDTO,
        InjuryDTO,
        PlayerStateDTO,
        StandingRowDTO,
        StandingsDTO,
    )

    try:
        block = _map_request(request)
        outcome = SeasonSimulation(block, rng, simulator).run()
    except (ValueError, TypeError, KeyError, AttributeError) as error:
        raise InvalidValueError(f"invalid block input: {error}") from error
    results = tuple(_report(p, block.managed_team.club_season_id) for p in outcome.results)
    tables = tuple(
        StandingsDTO(
            t.snapshot.competition_id,
            t.snapshot.as_of,
            tuple(
                StandingRowDTO(
                    r.club_season_id,
                    i,
                    r.played,
                    r.won,
                    r.drawn,
                    r.lost,
                    r.goals_for,
                    r.goals_against,
                    r.points,
                )
                for i, r in enumerate(t.snapshot.rows, 1)
            ),
            t.snapshot.stage_id,
            t.snapshot.group_id,
            t.unresolved,
        )
        for t in outcome.tables
    )
    return BlockSummaryDTO(
        request.block_id,
        results,
        tuple(r.fixture_id for r in results if r.key),
        tables,
        injuries=tuple(InjuryDTO(i.player_id, i.date, i.days, i.forced) for i in outcome.injuries),
        player_states=tuple(
            PlayerStateDTO(p.player_id, p.fitness, p.injured_until, p.minutes)
            for p in outcome.states
        ),
        unresolved_knockout_ties=(),
    )


def simulate_block(request: BlockSimRequest, rng: RandomSource) -> BlockSummaryDTO:
    """Simulate an inclusive block with stable root streams and immutable original baselines."""
    return _simulate(request, rng, PoissonMatchSimulator())
