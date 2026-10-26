"""Validate published DTOs and translate to the private pure season coordinator."""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from typing import TYPE_CHECKING, Literal, cast

type EventKind = Literal["advanced", "eliminated", "champion"]

from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import BlockId, ClubSeasonId, CompetitionId, FixtureId, PlayerId
from mister.simulation.domain.injuries import Injury
from mister.simulation.domain.groups import GroupMatch, GroupRules
from mister.simulation.domain.knockout import HistoricalBracket, HistoricalTie, KnockoutRules, KnockoutTie
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
    GroupEntry,
    HistoricalEvidence,
    Stage,
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
        CompetitionInput,
        SeasonSimInput,
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
        Morale(p.morale)
        Fitness(p.fitness)
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


def _stages(value: CompetitionInput) -> tuple[Stage, ...]:
    stages = []
    for stage in value.stages:
        if not stage.stage_id.strip():
            raise InvalidValueError("a stage needs an ID")
        if stage.round == "group_stage":
            if stage.points_per_win is None or stage.points_per_draw is None or stage.advance_per_group is None:
                raise InvalidValueError("groups need explicit scoring and qualification rules")
            if stage.reapply_head_to_head is None and any(t.startswith("head_to_head") for t in stage.tiebreakers):
                raise InvalidValueError("direct group criteria require an explicit reapplication rule")
            rules = GroupRules(stage.points_per_win, stage.points_per_draw, stage.tiebreakers,
                stage.advance_per_group, stage.reapply_head_to_head if stage.reapply_head_to_head is not None else False)
            groups = tuple((g.group_id, g.participants) for g in stage.groups)
            _unique(tuple(g[0] for g in groups), "group IDs")
            members = tuple(c for _, clubs in groups for c in clubs)
            _unique(members, "group participants")
            if not groups or not set(members) <= set(value.participants) or any(len(clubs) != 4 for _, clubs in groups):
                raise InvalidValueError("groups need four distinct competition participants")
            if type(stage.legs) is not int or stage.legs not in (1, 2):
                raise InvalidValueError("group repetitions must be one or two")
            stages.append(Stage(stage.stage_id, stage.round, groups=groups, group_rules=rules,
                                group_rounds=stage.legs))
        else:
            if stage.groups:
                raise InvalidValueError("knockout rounds cannot contain groups")
            stages.append(Stage(stage.stage_id, stage.round, KnockoutRules(stage.legs,
                stage.away_goals_rule, stage.extra_time, stage.penalties, stage.away_goals_in_extra_time)))
    _unique(tuple(s.stage_id for s in stages), "stage IDs")
    if value.kind != "league" and not stages:
        raise InvalidValueError("a knockout competition needs stages")
    return tuple(stages)


def _sources(sources: tuple[str, ...], verify: str) -> None:
    if verify != "ok" or not isinstance(sources, tuple) or not sources or any(
        not isinstance(source, str) or not source.strip() for source in sources):
        raise InvalidValueError("required historical evidence needs verified nonempty sources")


def _slots(season: SeasonSimInput, competitions: tuple[Competition, ...],
           fixtures: tuple[SeasonFixture, ...]) -> tuple[SeasonFixture, ...]:
    declarations = season.knockout_calendar or ()
    _unique(tuple(d.competition_id for d in declarations), "knockout calendar declarations")
    calendars = {d.competition_id: d for d in declarations}
    originals = {f.spec.fixture_id: f for f in fixtures}
    slots = []
    for competition in competitions:
        if competition.kind == "league":
            continue
        declaration = calendars.get(competition.competition_id)
        if declaration is None or declaration.slots is None:
            raise InvalidValueError("missing knockout calendar slots for a reachable competition")
        _sources(declaration.sources, declaration.verify)
        stage_ids = {s.stage_id for s in competition.stages if not s.groups}
        for slot in declaration.slots:
            _sources(slot.sources, slot.verify)
            if slot.date is None or slot.venue is None or slot.stage_id not in stage_ids:
                raise InvalidValueError("knockout slot needs known date, venue and knockout stage")
            if not {slot.home, slot.away} <= set(competition.participants):
                raise InvalidValueError("slot clubs must participate in the competition")
            spec = FixtureSpec(slot.fixture_id, _date(slot.date), competition.competition_id,
                slot.home, slot.away, Venue(slot.venue), True, slot.leg, slot.stage_id)
            original = originals.get(slot.fixture_id)
            if original is not None and replace(original.spec, key=True) != spec:
                raise InvalidValueError("knockout slot contradicts the managed historical fixture")
            slots.append(SeasonFixture(spec, original.round if original else None,
                                      original.historical if original else None))
        for stage in competition.stages:
            if stage.groups:
                continue
            ties = [t for t in competition.ties if t.stage_id == stage.stage_id]
            if not ties:
                raise InvalidValueError("a knockout stage needs historical ties")
            for historical in ties:
                calendar = tuple(f.spec for f in sorted(slots, key=lambda f: (f.spec.date, str(f.spec.fixture_id)))
                    if f.spec.competition_id == competition.competition_id and f.spec.stage == stage.stage_id
                    and {f.spec.home, f.spec.away} == set(historical.clubs))
                if stage.knockout_rules is None:
                    raise InvalidValueError("a knockout stage needs rules")
                KnockoutTie(stage.knockout_rules, calendar)
    _unique(tuple(f.spec.fixture_id for f in slots), "knockout slots")
    for fixture in fixtures:
        if fixture.spec.stage is not None and fixture.spec.group is None and fixture.spec.fixture_id not in {
            f.spec.fixture_id for f in slots}:
            raise InvalidValueError("a managed knockout fixture must match a historical slot")
    return tuple(slots)


def _evidence(season: SeasonSimInput, fixtures: tuple[SeasonFixture, ...]) -> tuple[HistoricalEvidence, ...]:
    evidence = []
    own = {f.spec.fixture_id: f for f in fixtures}
    for declaration in season.head_to_head or ():
        _sources(declaration.sources, declaration.verify)
        _unique(declaration.covered_clubs, "evidence participants")
        _unique(tuple(f.fixture_id for f in declaration.schedule), "evidence fixtures")
        _unique(tuple(r.fixture_id for r in declaration.results), "evidence results")
        scores = {r.fixture_id: r for r in declaration.results}
        schedule = []
        matches = []
        for fixture in declaration.schedule:
            _sources(fixture.sources, fixture.verify)
            if fixture.venue is None:
                raise InvalidValueError("historical fixture venue remains unknown")
            spec = FixtureSpec(fixture.fixture_id, _date(fixture.date), declaration.competition_id,
                fixture.home, fixture.away, Venue(fixture.venue), stage=declaration.stage_id,
                group=declaration.group_id)
            if not {spec.home, spec.away} <= set(declaration.covered_clubs):
                raise InvalidValueError("fixture lies outside historical evidence coverage")
            original = own.get(spec.fixture_id)
            if original is not None and replace(original.spec, key=False) != replace(spec, key=False):
                raise InvalidValueError("historical evidence contradicts a managed fixture")
            schedule.append(spec)
            result = scores.get(spec.fixture_id)
            if result is not None and result.score is not None and result.verify == "ok":
                _sources(result.sources, result.verify)
                score = Score(*result.score)
                if original is not None and original.historical is not None and original.historical != score:
                    raise InvalidValueError("evidence contradicts the managed historical score")
                matches.append(GroupMatch(spec, score))
        if not set(scores) <= {f.fixture_id for f in schedule}:
            raise InvalidValueError("historical result has no scheduled fixture")
        evidence.append(HistoricalEvidence(declaration.competition_id, _date(declaration.complete_through),
            declaration.covered_clubs, tuple(schedule), tuple(matches), declaration.sources,
            declaration.stage_id, declaration.group_id))
    _unique(tuple((e.competition_id, e.complete_through, e.stage_id, e.group_id) for e in evidence),
            "historical evidence cutoffs")
    return tuple(evidence)


def _entries(season: SeasonSimInput, competitions: tuple[Competition, ...],
             snapshots: tuple[TableSnapshot, ...]) -> tuple[GroupEntry, ...]:
    declarations = season.group_entry_assignments or ()
    _unique(tuple(d.competition_id for d in declarations), "group entry declarations")
    entries = []
    for declaration in declarations:
        if declaration.entries is None:
            continue
        _sources(declaration.sources, declaration.verify)
        for entry in declaration.entries:
            _sources(entry.sources, entry.verify)
            entries.append(GroupEntry(declaration.competition_id, entry.source_stage_id, entry.group_id,
                entry.qualifying_position, entry.target_stage_id, entry.historical_representative))
    for competition in competitions:
        for index, stage in enumerate(competition.stages):
            if not stage.groups or index == len(competition.stages)-1:
                continue
            target = competition.stages[index+1]
            selected = [e for e in entries if e.competition_id == competition.competition_id
                        and e.source_stage_id == stage.stage_id]
            expected = {(group, position) for group, _ in stage.groups for position in
                        range(1, (stage.group_rules.advance_per_group if stage.group_rules else 0)+1)}
            if len(selected) != len(expected) or {(e.group_id, e.position) for e in selected} != expected:
                raise InvalidValueError("group entries must cover every qualifying position exactly once")
            representatives = {c for t in competition.ties if t.stage_id == target.stage_id for c in t.clubs}
            if {e.representative for e in selected} != representatives or any(
                e.target_stage_id != target.stage_id for e in selected):
                raise InvalidValueError("group entries must exactly cover the first knockout stage")
            for entry in selected:
                candidates = [s for s in snapshots if (s.competition_id, s.stage_id, s.group_id) ==
                    (competition.competition_id, stage.stage_id, entry.group_id)]
                if not candidates or max(candidates, key=lambda s: s.as_of).order[entry.position-1] != entry.representative:
                    raise InvalidValueError("historical group entry must agree with the original final order")
    return tuple(entries)


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
                _stages(c),
                tuple(HistoricalTie(t.stage_id, t.clubs, t.winner) for t in c.real_ties),
            )
        )
    _unique(tuple(c.competition_id for c in competitions), "competitions")
    for competition in competitions:
        knockout_stages = tuple(s.stage_id for s in competition.stages if not s.groups)
        if knockout_stages:
            HistoricalBracket(knockout_stages, competition.ties)
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
    slots = _slots(season, tuple(competitions), fixtures)
    fixture_map = {f.spec.fixture_id: f for f in (*fixtures, *slots)}
    _unique(tuple(r.fixture_id for r in value.prior_results), "prior results")
    prior = []
    for result in value.prior_results:
        fixture = fixture_map.get(result.fixture_id)
        if fixture is None or result.date >= start:
            raise InvalidValueError("prior result must identify an earlier scheduled fixture")
        if fixture.spec.group is None and competition_map[fixture.spec.competition_id].kind != "league":
            fixture = replace(fixture, spec=replace(fixture.spec, home=result.home, away=result.away))
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
    injuries = tuple(dict.fromkeys(
        Injury(i.player_id, _date(i.date), i.days, True)
        for i in (*season.forced_injuries, *value.forced_injuries_from_effects)
    ))
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
        _evidence(season, fixtures),
        priorities,
        injuries,
        {
            p.player_id: p.injured_until
            for p in value.managed_team.players
            if p.injured_until is not None
        },
        frozenset(p.player_id for p in value.managed_team.players if p.youth_minutes),
        tuple(prior),
        slots,
        _entries(season, tuple(competitions), tuple(snapshots)),
        tuple((club, p.player_id, p.injured_until)
              for club, source in {t.club_season_id: t for t in
                  (*season.teams, *value.team_overrides)}.items()
              if isinstance(source, SquadTeamInput) and club != season.managed_club_season_id
              for p in source.players if p.injured_until is not None),
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
        CompetitionInput,
        SeasonSimInput,
        InjuryDTO,
        PlayerStateDTO,
        EventDTO,
        UnresolvedKnockoutTieDTO,
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
        events=tuple(EventDTO(cast("EventKind", e.kind), e.date,
            block.managed_team.club_season_id, e.competition_id, e.stage_id) for e in outcome.events),
        unresolved_knockout_ties=tuple(UnresolvedKnockoutTieDTO(t.fixtures[0].competition_id,
            t.fixtures[0].stage or "", (t.fixtures[0].home, t.fixtures[0].away),
            tuple(f.fixture_id for f in t.fixtures)) for t in outcome.unresolved),
    )


def simulate_block(request: BlockSimRequest, rng: RandomSource) -> BlockSummaryDTO:
    """Simulate an inclusive block with stable root streams and immutable original baselines."""
    return _simulate(request, rng, PoissonMatchSimulator())
