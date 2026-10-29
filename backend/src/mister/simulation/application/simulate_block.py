"""Validate published DTOs and translate to the private pure season coordinator."""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from typing import TYPE_CHECKING, Literal, cast

from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import BlockId, ClubSeasonId, CompetitionId, FixtureId, PlayerId
from mister.simulation.application import api as dto
from mister.simulation.domain.dated_squads import DatedMembership, validate_memberships
from mister.simulation.domain.groups import GroupMatch, GroupRules
from mister.simulation.domain.injuries import Injury
from mister.simulation.domain.knockout import (
    HistoricalBracket,
    HistoricalTie,
    KnockoutRules,
    KnockoutTie,
)
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
    KeyStarterChoice,
    PlayedMatch,
    SeasonFixture,
    SeasonSimulation,
    Stage,
    TableSnapshot,
)
from mister.simulation.domain.season import project_lineup as project_block_lineup

if TYPE_CHECKING:
    from mister.shared_kernel.randomness import RandomSource
    from mister.simulation.domain.ports import MatchSimulator


type EventKind = Literal["advanced", "eliminated", "champion"]


_GROUP_SIZE = 4
_MIN_PARTICIPANTS = 2


def _one_or_two(value: object) -> int:
    if type(value) is not int or value not in (1, 2):
        raise InvalidValueError("round count must be one or two")
    return value


def _date(value: date) -> date:
    if type(value) is not date:
        raise InvalidValueError("a calendar date is required")
    return value


def _unique(values: tuple[object, ...], name: str) -> None:
    if len(values) != len(set(values)):
        raise InvalidValueError(f"duplicate {name}")


def _team(value: dto.TeamInput, *, morale: int = 50, neutral: bool = False) -> SimTeam:

    if not isinstance(value.club_season_id, ClubSeasonId):
        raise InvalidValueError("team needs a typed club ID")
    if isinstance(value, dto.AggregateTeamInput):
        return SimTeam(
            value.club_season_id, aggregate=AggregateIndices(value.attack, value.defense)
        )
    if not isinstance(value, dto.SquadTeamInput):
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

    if not isinstance(value, dto.FixtureInput):
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


def _record(
    value: dto.MatchResultDTO, fixture: SeasonFixture, managed: ClubSeasonId
) -> PlayedMatch:

    if not isinstance(value, dto.MatchResultDTO):
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


def _stages(value: dto.CompetitionInput) -> tuple[Stage, ...]:
    stages = []
    for stage in value.stages:
        if not stage.stage_id.strip():
            raise InvalidValueError("a stage needs an ID")
        if stage.round == "group_stage":
            if (
                stage.points_per_win is None
                or stage.points_per_draw is None
                or stage.advance_per_group is None
            ):
                raise InvalidValueError("groups need explicit scoring and qualification rules")
            if stage.reapply_head_to_head is None and any(
                t.startswith("head_to_head") for t in stage.tiebreakers
            ):
                raise InvalidValueError(
                    "direct group criteria require an explicit reapplication rule"
                )
            rules = GroupRules(
                stage.points_per_win,
                stage.points_per_draw,
                stage.tiebreakers,
                stage.advance_per_group,
                stage.reapply_head_to_head if stage.reapply_head_to_head is not None else False,
                stage.coefficients,
            )
            groups = tuple((g.group_id, g.participants) for g in stage.groups)
            _unique(tuple(g[0] for g in groups), "group IDs")
            members = tuple(c for _, clubs in groups for c in clubs)
            _unique(members, "group participants")
            if (
                not groups
                or not set(members) <= set(value.participants)
                or any(len(clubs) != _GROUP_SIZE for _, clubs in groups)
            ):
                raise InvalidValueError("groups need four distinct competition participants")
            _one_or_two(stage.legs)
            stages.append(
                Stage(
                    stage.stage_id,
                    stage.round,
                    groups=groups,
                    group_rules=rules,
                    group_rounds=stage.legs,
                )
            )
        else:
            if stage.groups:
                raise InvalidValueError("knockout rounds cannot contain groups")
            stages.append(
                Stage(
                    stage.stage_id,
                    stage.round,
                    KnockoutRules(
                        stage.legs,
                        stage.away_goals_rule,
                        stage.extra_time,
                        stage.penalties,
                        stage.away_goals_in_extra_time,
                    ),
                )
            )
    _unique(tuple(s.stage_id for s in stages), "stage IDs")
    if value.kind != "league" and not stages:
        raise InvalidValueError("a knockout competition needs stages")
    return tuple(stages)


def _sources(sources: tuple[str, ...], verify: str) -> None:
    if (
        verify != "ok"
        or not isinstance(sources, tuple)
        or not sources
        or any(not isinstance(source, str) or not source.strip() for source in sources)
    ):
        raise InvalidValueError("required historical evidence needs verified nonempty sources")


def _check_feeders(slots: tuple[SeasonFixture, ...], competitions: tuple[Competition, ...]) -> None:
    for competition in competitions:
        for index, stage in enumerate(competition.stages):
            if index == 0 or competition.stages[index - 1].groups:
                continue
            previous = competition.stages[index - 1]
            for fixture in (
                f
                for f in slots
                if f.spec.competition_id == competition.competition_id
                and f.spec.stage == stage.stage_id
            ):
                for club in (fixture.spec.home, fixture.spec.away):
                    feeders = [
                        t
                        for t in competition.ties
                        if t.stage_id == previous.stage_id and t.winner == club
                    ]
                    if len(feeders) != 1:
                        raise InvalidValueError("a knockout slot needs a unique historical feeder")
                    dates = [
                        f.spec.date
                        for f in slots
                        if f.spec.competition_id == competition.competition_id
                        and f.spec.stage == previous.stage_id
                        and {f.spec.home, f.spec.away} == set(feeders[0].clubs)
                    ]
                    if not dates or max(dates) >= fixture.spec.date:
                        raise InvalidValueError("knockout slot date must follow its feeder tie")


def _slot(
    slot: dto.KnockoutSlotInput,
    competition: Competition,
    stage_ids: set[str],
    originals: dict[FixtureId, SeasonFixture],
) -> SeasonFixture:
    _sources(slot.sources, slot.verify)
    if slot.date is None or slot.venue is None or slot.stage_id not in stage_ids:
        raise InvalidValueError("knockout slot needs known date, venue and knockout stage")
    if not {slot.home, slot.away} <= set(competition.participants):
        raise InvalidValueError("slot clubs must participate in the competition")
    spec = FixtureSpec(
        slot.fixture_id,
        _date(slot.date),
        competition.competition_id,
        slot.home,
        slot.away,
        Venue(slot.venue),
        True,
        slot.leg,
        slot.stage_id,
    )
    original = originals.get(slot.fixture_id)
    if original is not None and replace(original.spec, key=True) != spec:
        raise InvalidValueError("knockout slot contradicts the managed historical fixture")
    return SeasonFixture(
        spec,
        original.round if original else None,
        original.historical if original else None,
    )


def _slots(
    season: dto.SeasonSimInput,
    competitions: tuple[Competition, ...],
    fixtures: tuple[SeasonFixture, ...],
) -> tuple[SeasonFixture, ...]:
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
            slots.append(_slot(slot, competition, stage_ids, originals))
        for stage in competition.stages:
            if stage.groups:
                continue
            ties = [t for t in competition.ties if t.stage_id == stage.stage_id]
            if not ties:
                raise InvalidValueError("a knockout stage needs historical ties")
            for historical in ties:
                calendar = tuple(
                    f.spec
                    for f in sorted(slots, key=lambda f: (f.spec.date, str(f.spec.fixture_id)))
                    if f.spec.competition_id == competition.competition_id
                    and f.spec.stage == stage.stage_id
                    and {f.spec.home, f.spec.away} == set(historical.clubs)
                )
                if stage.knockout_rules is None:
                    raise InvalidValueError("a knockout stage needs rules")
                KnockoutTie(stage.knockout_rules, calendar)
    _unique(tuple(f.spec.fixture_id for f in slots), "knockout slots")
    for fixture in fixtures:
        if (
            fixture.spec.stage is not None
            and fixture.spec.group is None
            and fixture.spec.fixture_id not in {f.spec.fixture_id for f in slots}
        ):
            raise InvalidValueError("a managed knockout fixture must match a historical slot")
    _check_feeders(tuple(slots), competitions)
    return tuple(slots)


def _table_scope(
    competition: Competition,
    stage_id: str | None,
    group_id: str | None,
) -> tuple[tuple[ClubSeasonId, ...], Stage | None]:
    if competition.kind == "league":
        if stage_id is not None or group_id is not None:
            raise InvalidValueError("league tables and evidence cannot identify a group stage")
        return competition.participants, None
    stage = next((s for s in competition.stages if s.stage_id == stage_id), None)
    if stage is None or not stage.groups:
        raise InvalidValueError("table or evidence needs a declared group stage")
    participants = next((clubs for group, clubs in stage.groups if group == group_id), None)
    if participants is None:
        raise InvalidValueError("table or evidence needs a declared group ID")
    return participants, stage


def _fixture_scope(spec: FixtureSpec, competition: Competition) -> None:
    if competition.kind == "league":
        if spec.stage is not None or spec.group is not None or spec.leg is not None:
            raise InvalidValueError("a league fixture cannot carry group or knockout metadata")
        return
    stage = next((s for s in competition.stages if s.stage_id == spec.stage), None)
    if stage is None:
        raise InvalidValueError("fixture needs a declared competition stage")
    if stage.groups:
        participants, _ = _table_scope(competition, spec.stage, spec.group)
        if not {spec.home, spec.away} <= set(participants) or spec.leg is not None:
            raise InvalidValueError("group fixture sides must belong to its declared group")
    elif spec.group is not None:
        raise InvalidValueError("a knockout fixture cannot identify a group")


def _evidence(
    season: dto.SeasonSimInput,
    fixtures: tuple[SeasonFixture, ...],
    competition_map: dict[CompetitionId, Competition],
) -> tuple[HistoricalEvidence, ...]:
    evidence = []
    own = {f.spec.fixture_id: f for f in fixtures}
    for declaration in season.head_to_head or ():
        _sources(declaration.sources, declaration.verify)
        if declaration.competition_id not in competition_map:
            raise InvalidValueError("historical evidence identifies an unknown competition")
        participants, _ = _table_scope(
            competition_map[declaration.competition_id], declaration.stage_id, declaration.group_id
        )
        if not declaration.covered_clubs or not set(declaration.covered_clubs) <= set(participants):
            raise InvalidValueError("historical evidence coverage must belong to its table scope")
        _unique(declaration.covered_clubs, "evidence participants")
        _unique(tuple(f.fixture_id for f in declaration.schedule), "evidence fixtures")
        _unique(tuple(r.fixture_id for r in declaration.results), "evidence results")
        scores = {r.fixture_id: r for r in declaration.results}
        schedule = []
        matches = []
        unknown_venues = set()
        for fixture in declaration.schedule:
            _sources(fixture.sources, fixture.verify)
            original = own.get(fixture.fixture_id)
            venue = (
                Venue(fixture.venue)
                if fixture.venue is not None
                else (original.spec.venue if original is not None else Venue.NEUTRAL)
            )
            if fixture.venue is None and original is None:
                unknown_venues.add(fixture.fixture_id)
            spec = FixtureSpec(
                fixture.fixture_id,
                _date(fixture.date),
                declaration.competition_id,
                fixture.home,
                fixture.away,
                venue,
                stage=declaration.stage_id,
                group=declaration.group_id,
            )
            if not {spec.home, spec.away} <= set(declaration.covered_clubs):
                raise InvalidValueError("fixture lies outside historical evidence coverage")
            original = own.get(spec.fixture_id)
            if original is not None and replace(original.spec, key=False) != replace(
                spec, key=False
            ):
                raise InvalidValueError("historical evidence contradicts a managed fixture")
            schedule.append(spec)
            result = scores.get(spec.fixture_id)
            if result is not None and result.score is not None and result.verify == "ok":
                _sources(result.sources, result.verify)
                score = Score(*result.score)
                if (
                    original is not None
                    and original.historical is not None
                    and original.historical != score
                ):
                    raise InvalidValueError("evidence contradicts the managed historical score")
                matches.append(GroupMatch(spec, score))
        if not set(scores) <= {f.fixture_id for f in schedule}:
            raise InvalidValueError("historical result has no scheduled fixture")
        evidence.append(
            HistoricalEvidence(
                declaration.competition_id,
                _date(declaration.complete_through),
                declaration.covered_clubs,
                tuple(schedule),
                tuple(matches),
                declaration.sources,
                declaration.stage_id,
                declaration.group_id,
                frozenset(unknown_venues),
            )
        )
    _unique(
        tuple((e.competition_id, e.complete_through, e.stage_id, e.group_id) for e in evidence),
        "historical evidence cutoffs",
    )
    return tuple(evidence)


def _qualifying_position(value: object) -> int:
    if type(value) is not int or value <= 0:
        raise InvalidValueError("qualifying position must be an exact positive integer")
    return value


def _entries(
    season: dto.SeasonSimInput,
    competitions: tuple[Competition, ...],
    snapshots: tuple[TableSnapshot, ...],
) -> tuple[GroupEntry, ...]:
    declarations = season.group_entry_assignments or ()
    _unique(tuple(d.competition_id for d in declarations), "group entry declarations")
    entries = []
    for declaration in declarations:
        if declaration.entries is None:
            continue
        _sources(declaration.sources, declaration.verify)
        for source_entry in declaration.entries:
            _sources(source_entry.sources, source_entry.verify)
            entries.append(
                GroupEntry(
                    declaration.competition_id,
                    source_entry.source_stage_id,
                    source_entry.group_id,
                    _qualifying_position(source_entry.qualifying_position),
                    source_entry.target_stage_id,
                    source_entry.historical_representative,
                )
            )
    for competition in competitions:
        for index, stage in enumerate(competition.stages):
            if not stage.groups or index == len(competition.stages) - 1:
                continue
            target = competition.stages[index + 1]
            selected = [
                e
                for e in entries
                if e.competition_id == competition.competition_id
                and e.source_stage_id == stage.stage_id
            ]
            expected = {
                (group, position)
                for group, _ in stage.groups
                for position in range(
                    1, (stage.group_rules.advance_per_group if stage.group_rules else 0) + 1
                )
            }
            if (
                len(selected) != len(expected)
                or {(e.group_id, e.position) for e in selected} != expected
            ):
                raise InvalidValueError(
                    "group entries must cover every qualifying position exactly once"
                )
            representatives = {
                c for t in competition.ties if t.stage_id == target.stage_id for c in t.clubs
            }
            if {e.representative for e in selected} != representatives or any(
                e.target_stage_id != target.stage_id for e in selected
            ):
                raise InvalidValueError("group entries must exactly cover the first knockout stage")
            for entry in selected:
                candidates = [
                    s
                    for s in snapshots
                    if (s.competition_id, s.stage_id, s.group_id)
                    == (competition.competition_id, stage.stage_id, entry.group_id)
                ]
                if not candidates:
                    raise InvalidValueError("group entry needs an original final table")
                final = max(candidates, key=lambda s: s.as_of)
                if any(entry.representative in tied for tied in final.unresolved_ties or ()):
                    raise InvalidValueError(
                        "unresolved historical positions cannot justify group entry slots"
                    )
                if final.order[entry.position - 1] != entry.representative:
                    raise InvalidValueError(
                        "historical group entry must agree with the original final order"
                    )
    return tuple(entries)


def _competitions(
    season: dto.SeasonSimInput, team_ids: set[ClubSeasonId]
) -> tuple[Competition, ...]:
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
            len(c.participants) < _MIN_PARTICIPANTS
            or not set(c.participants) <= team_ids
            or (season.managed_club_season_id not in c.participants)
        ):
            raise InvalidValueError("invalid competition participants")
        if c.kind == "league":
            _one_or_two(c.rounds)
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
    return tuple(competitions)


def _orient_fixtures(
    fixtures: tuple[SeasonFixture, ...],
    competition_map: dict[CompetitionId, Competition],
    managed: ClubSeasonId,
) -> tuple[SeasonFixture, ...]:
    for fixture in fixtures:
        spec = fixture.spec
        effective_competition = competition_map.get(spec.competition_id)
        if (
            effective_competition is None
            or not {spec.home, spec.away} <= set(effective_competition.participants)
            or (managed not in (spec.home, spec.away))
        ):
            raise InvalidValueError("fixture must belong to managed team and its competition")
        _fixture_scope(spec, effective_competition)
    return tuple(
        SeasonFixture(
            f.spec,
            f.round,
            (
                Score(f.historical.away, f.historical.home)
                if f.spec.away == managed and f.historical is not None
                else f.historical
            ),
        )
        for f in fixtures
    )


def _prior_results(
    value: dto.BlockSimRequest,
    fixtures: tuple[SeasonFixture, ...],
    slots: tuple[SeasonFixture, ...],
    competition_map: dict[CompetitionId, Competition],
) -> tuple[PlayedMatch, ...]:
    fixture_map = {f.spec.fixture_id: f for f in (*fixtures, *slots)}
    _unique(tuple(r.fixture_id for r in value.prior_results), "prior results")
    prior = []
    for result in value.prior_results:
        prior_fixture = fixture_map.get(result.fixture_id)
        if value.state_as_of is not None and result.date > value.state_as_of:
            raise InvalidValueError("incoming state cursor cannot precede a prior match")
        if prior_fixture is None or result.date >= value.start:
            raise InvalidValueError("prior result must identify an earlier scheduled fixture")
        if (
            prior_fixture.spec.group is None
            and competition_map[prior_fixture.spec.competition_id].kind != "league"
        ):
            prior_fixture = replace(
                prior_fixture, spec=replace(prior_fixture.spec, home=result.home, away=result.away)
            )
        prior.append(_record(result, prior_fixture, value.season.managed_club_season_id))
    return tuple(prior)


def _snapshots(
    season: dto.SeasonSimInput, competition_map: dict[CompetitionId, Competition]
) -> tuple[TableSnapshot, ...]:
    snapshots = []
    for snapshot in season.historical_standings:
        if snapshot.competition_id not in competition_map:
            raise InvalidValueError("table belongs to unknown competition")
        competition = competition_map[snapshot.competition_id]
        participants, stage = _table_scope(competition, snapshot.stage_id, snapshot.group_id)
        clubs = tuple(r.club_season_id for r in snapshot.rows)
        if len(clubs) != len(participants) or set(clubs) != set(participants):
            raise InvalidValueError(
                "historical snapshot rows must cover every participant exactly once"
            )
        positions = tuple(r.position for r in snapshot.rows)
        if any(type(position) is not int for position in positions) or set(positions) != set(
            range(1, len(clubs) + 1)
        ):
            raise InvalidValueError(
                "snapshot positions must be distinct consecutive positive integers"
            )
        rules = stage.group_rules if stage else None
        ppw = rules.points_per_win if rules else competition.points_per_win
        ppd = rules.points_per_draw if rules else competition.points_per_draw
        if any(r.points != r.won * ppw + r.drawn * ppd for r in snapshot.rows):
            raise InvalidValueError("original table points must follow the declared scoring rules")
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
                snapshot.unresolved_ties,
            )
        )
    _unique(
        tuple((s.competition_id, s.as_of, s.stage_id, s.group_id) for s in snapshots), "snapshots"
    )
    return tuple(snapshots)


def _dated_squad_inputs(
    value: dto.BlockSimRequest,
    team_ids: set[ClubSeasonId],
    reference_teams: dict[ClubSeasonId, dto.TeamInput],
) -> tuple[tuple[DatedMembership, ...] | None, tuple[SimPlayer, ...] | None]:
    if (value.squad_memberships is None) != (value.player_pool is None):
        raise InvalidValueError("dated memberships and player pool must be supplied together")
    if value.squad_memberships is None or value.player_pool is None:
        return None, None
    if not isinstance(value.squad_memberships, tuple) or not isinstance(value.player_pool, tuple):
        raise InvalidValueError("dated squad collections must be immutable tuples")
    if any(not isinstance(item, dto.SquadMembershipInput) for item in value.squad_memberships):
        raise InvalidValueError("squad_memberships must contain SquadMembershipInput values")
    if any(item.club_season_id not in team_ids for item in value.squad_memberships):
        raise InvalidValueError("squad membership refers to an unknown club-season")
    if any(
        isinstance(reference_teams[item.club_season_id], dto.AggregateTeamInput)
        for item in value.squad_memberships
    ):
        raise InvalidValueError("dated ownership cannot partially replace an aggregate rival")
    memberships = tuple(
        DatedMembership(item.player_id, item.club_season_id, item.joined_on, item.left_on)
        for item in value.squad_memberships
    )
    validate_memberships(memberships)
    pool_ids = tuple(player.player_id for player in value.player_pool)
    _unique(pool_ids, "player pool players")
    if not {item.player_id for item in memberships} <= set(pool_ids):
        raise InvalidValueError("squad membership refers to a player outside player_pool")
    if not {player.player_id for player in value.managed_team.players} <= set(pool_ids):
        raise InvalidValueError("player_pool must include the managed squad state")
    pool_team = _team(
        dto.SquadTeamInput(
            value.season.managed_club_season_id,
            value.player_pool,
            value.managed_team.tactic,
        ),
        morale=value.team_morale,
    )
    return memberships, cast("tuple[SimPlayer, ...]", pool_team.squad)


def _block_fixture(
    value: dto.BlockSimRequest, block: Block, fixture_id: FixtureId
) -> SeasonFixture:
    """An unplayed managed fixture of the season calendar dated inside the block."""
    fixture = next((f for f in block.fixtures if f.spec.fixture_id == fixture_id), None)
    if (
        fixture is None
        or not value.start <= fixture.spec.date <= value.end
        or any(item.fixture.spec.fixture_id == fixture_id for item in block.prior)
    ):
        raise InvalidValueError("fixture must be an unplayed managed fixture of the block")
    return fixture


def _key_starter(value: dto.BlockSimRequest, block: Block) -> KeyStarterChoice | None:
    selection = value.key_starter
    if selection is None:
        return None
    if not isinstance(selection, dto.KeyStarterSelection):
        raise InvalidValueError("key starter must be a typed selection")
    fixture = _block_fixture(value, block, selection.fixture_id)
    if fixture.spec.date != selection.date:
        raise InvalidValueError("key starter date must match its fixture")
    known = block.player_pool if block.player_pool is not None else block.managed_team.squad
    if selection.player_id not in {p.player_id for p in known or ()}:
        raise InvalidValueError("key starter refers to an unknown player")
    return KeyStarterChoice(selection.fixture_id, selection.date, selection.player_id)


def _map_request(value: dto.BlockSimRequest) -> Block:
    block = _map_block(value)
    return replace(block, key_starter=_key_starter(value, block))


def _map_block(value: dto.BlockSimRequest) -> Block:

    season = value.season
    if not isinstance(value.block_id, BlockId):
        raise InvalidValueError("block needs a typed ID")
    start, end = _date(value.start), _date(value.end)
    state_as_of = start if value.state_as_of is None else _date(value.state_as_of)
    if end < start or state_as_of > start:
        raise InvalidValueError("invalid block range or state date")
    if not isinstance(value.managed_team, dto.SquadTeamInput) or (
        value.managed_team.club_season_id != season.managed_club_season_id
    ):
        raise InvalidValueError("managed squad must identify the season's managed club")
    references = tuple(_team(t, neutral=True) for t in season.teams)
    _unique(tuple(t.club_season_id for t in references), "reference teams")
    team_ids = {t.club_season_id for t in references}
    if season.managed_club_season_id not in team_ids:
        raise InvalidValueError("managed club needs an original reference squad")
    competitions = _competitions(season, team_ids)
    competition_ids = {c.competition_id for c in competitions}
    priorities = {}
    for competition_id, priority in value.competition_priorities.items():
        if competition_id not in competition_ids:
            raise InvalidValueError("priority refers to an unknown competition")
        priorities[competition_id] = Priority(priority)
    fixtures = tuple(_fixture(f) for f in season.fixtures)
    _unique(tuple(f.spec.fixture_id for f in fixtures), "fixtures")
    competition_map = {c.competition_id: c for c in competitions}
    fixtures = _orient_fixtures(fixtures, competition_map, season.managed_club_season_id)
    rivals = tuple(_team(t, neutral=True) for t in value.team_overrides)
    _unique(tuple(t.club_season_id for t in rivals), "team overrides")
    if any(
        t.club_season_id not in team_ids or t.club_season_id == season.managed_club_season_id
        for t in rivals
    ):
        raise InvalidValueError("override needs a known rival")
    memberships, player_pool = _dated_squad_inputs(
        value, team_ids, {team.club_season_id: team for team in season.teams}
    )
    slots = _slots(season, tuple(competitions), fixtures)
    prior = _prior_results(value, fixtures, slots, competition_map)
    snapshots = _snapshots(season, competition_map)
    injuries = tuple(
        dict.fromkeys(
            Injury(i.player_id, _date(i.date), i.days, True)
            for i in (*season.forced_injuries, *value.forced_injuries_from_effects)
        )
    )
    incoming_players = (
        value.player_pool if value.player_pool is not None else value.managed_team.players
    )
    squad_ids = {p.player_id for p in incoming_players}
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
        _evidence(season, fixtures, competition_map),
        priorities,
        injuries,
        {p.player_id: p.injured_until for p in incoming_players if p.injured_until is not None},
        frozenset(p.player_id for p in incoming_players if p.youth_minutes),
        tuple(prior),
        slots,
        _entries(season, tuple(competitions), tuple(snapshots)),
        tuple(
            (club, p.player_id, p.injured_until)
            for club, source in {
                t.club_season_id: t for t in (*season.teams, *value.team_overrides)
            }.items()
            if isinstance(source, dto.SquadTeamInput) and club != season.managed_club_season_id
            for p in source.players
            if p.injured_until is not None
        ),
        memberships,
        player_pool,
    )


def _report(played: PlayedMatch, managed: ClubSeasonId) -> dto.MatchResultDTO:

    fixture, result = played.fixture, played.result
    spec = fixture.spec
    winner = result.winner
    own_home = spec.home == managed
    user_result = (
        "draw" if winner is None else ("win" if (winner.value == "home") == own_home else "loss")
    )
    return dto.MatchResultDTO(
        spec.fixture_id,
        spec.competition_id,
        spec.date,
        spec.home,
        spec.away,
        (result.regulation.home, result.regulation.away),
        "neutral" if spec.venue is Venue.NEUTRAL else "home" if own_home else "away",
        spec.away if own_home else spec.home,
        cast("dto.UserResultName", user_result),
        (result.extra_time.home, result.extra_time.away) if result.extra_time is not None else None,
        (result.penalties.home, result.penalties.away) if result.penalties is not None else None,
        winner.value if winner is not None else None,
        spec.key,
        fixture.round,
        spec.stage,
        spec.group,
        cast("Literal[1, 2] | None", spec.leg),
    )


def _simulate(
    request: dto.BlockSimRequest, rng: RandomSource, simulator: MatchSimulator
) -> dto.BlockSummaryDTO:

    try:
        block = _map_request(request)
        outcome = SeasonSimulation(block, rng, simulator).run()
    except (ValueError, TypeError, KeyError, AttributeError) as error:
        raise InvalidValueError(f"invalid block input: {error}") from error
    results = tuple(_report(p, block.managed_team.club_season_id) for p in outcome.results)
    tables = tuple(
        dto.StandingsDTO(
            t.snapshot.competition_id,
            t.snapshot.as_of,
            tuple(
                dto.StandingRowDTO(
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
    return dto.BlockSummaryDTO(
        request.block_id,
        results,
        tuple(r.fixture_id for r in results if r.key),
        tables,
        injuries=tuple(
            dto.InjuryDTO(i.player_id, i.date, i.days, i.forced) for i in outcome.injuries
        ),
        player_states=tuple(
            dto.PlayerStateDTO(p.player_id, p.fitness, p.injured_until, p.minutes)
            for p in outcome.states
        ),
        events=tuple(
            dto.EventDTO(
                cast("EventKind", e.kind),
                e.date,
                block.managed_team.club_season_id,
                e.competition_id,
                e.stage_id,
            )
            for e in outcome.events
        ),
        unresolved_knockout_ties=tuple(
            dto.UnresolvedKnockoutTieDTO(
                t.fixtures[0].competition_id,
                t.fixtures[0].stage or "",
                (t.fixtures[0].home, t.fixtures[0].away),
                tuple(f.fixture_id for f in t.fixtures),
            )
            for t in outcome.unresolved
        ),
        key_starter_outcome=(
            dto.KeyStarterOutcome(
                outcome.key_starter.choice.fixture_id,
                outcome.key_starter.choice.date,
                outcome.key_starter.choice.player_id,
                outcome.key_starter.starter_ids,
                cast("dto.StarterAbsenceReason | None", outcome.key_starter.absence_reason),
            )
            if outcome.key_starter is not None
            else None
        ),
    )


def simulate_block(request: dto.BlockSimRequest, rng: RandomSource) -> dto.BlockSummaryDTO:
    """Simulate an inclusive block with stable root streams and immutable original baselines."""
    return _simulate(request, rng, PoissonMatchSimulator())


def project_lineup(
    request: dto.BlockSimRequest, fixture_id: FixtureId
) -> dto.LineupProjectionDTO | None:
    """Validate the whole request, then forecast without drawing from any random source."""
    try:
        block = _map_block(request)
        fixture = _block_fixture(request, block, fixture_id)
        projection = project_block_lineup(block, fixture.spec)
    except (ValueError, TypeError, KeyError, AttributeError) as error:
        raise InvalidValueError(f"invalid projection input: {error}") from error
    if projection is None:
        return None
    return dto.LineupProjectionDTO(projection.starter_ids, projection.reserve_ids)
