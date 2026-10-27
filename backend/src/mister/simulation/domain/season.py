"""Pure chronological block coordination, retaining original P2 and strength references."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import timedelta
from typing import TYPE_CHECKING, cast

from mister.shared_kernel.errors import InvalidValueError
from mister.simulation.domain.fitness import match_fitness, recover_between
from mister.simulation.domain.groups import (
    GroupEvidence,
    GroupMatch,
    GroupRules,
    GroupTable,
    _overall_value,
    _partition,
)
from mister.simulation.domain.injuries import Injury, injured_until, simulate_injury
from mister.simulation.domain.knockout import HistoricalTie, KnockoutRules, KnockoutTie
from mister.simulation.domain.league import (
    HeadToHeadEvidence,
    HeadToHeadFixture,
    HeadToHeadResult,
    HistoricalExternalResults,
    LeagueTable,
)
from mister.simulation.domain.league_types import (
    ExternalResultsRequest,
    LeagueRow,
    ResultReplacement,
)
from mister.simulation.domain.lineup import select_lineup
from mister.simulation.domain.model import (
    CompetitionParams,
    FixtureSpec,
    MatchResult,
    MatchSetup,
    Priority,
    Score,
    SimTeam,
)
from mister.simulation.domain.strength import StrengthReference, calculate_strength

_STARTERS = 11
_TWO_CLUBS = 2

if TYPE_CHECKING:
    from datetime import date

    from mister.shared_kernel.ids import ClubSeasonId, CompetitionId, FixtureId, PlayerId
    from mister.shared_kernel.randomness import RandomSource
    from mister.simulation.domain.model import SimPlayer, Tactic, Venue
    from mister.simulation.domain.ports import MatchSimulator


@dataclass(frozen=True, slots=True)
class SeasonFixture:
    spec: FixtureSpec
    round: int | None = None
    historical: Score | None = None


@dataclass(frozen=True, slots=True)
class TableSnapshot:
    competition_id: CompetitionId
    as_of: date
    rows: tuple[LeagueRow, ...]
    order: tuple[ClubSeasonId, ...]
    stage_id: str | None = None
    group_id: str | None = None
    unresolved_ties: tuple[tuple[ClubSeasonId, ...], ...] | None = None


@dataclass(frozen=True, slots=True)
class Competition:
    competition_id: CompetitionId
    kind: str
    participants: tuple[ClubSeasonId, ...]
    params: CompetitionParams
    rounds: int | None
    points_per_win: int
    points_per_draw: int
    tiebreakers: tuple[str, ...]
    stages: tuple[Stage, ...] = ()
    ties: tuple[HistoricalTie, ...] = ()


@dataclass(frozen=True, slots=True)
class Stage:
    stage_id: str
    round: str
    knockout_rules: KnockoutRules | None = None
    groups: tuple[tuple[str, tuple[ClubSeasonId, ...]], ...] = ()
    group_rules: GroupRules | None = None
    group_rounds: int = 1


@dataclass(frozen=True, slots=True)
class HistoricalEvidence:
    competition_id: CompetitionId
    complete_through: date
    participants: tuple[ClubSeasonId, ...]
    schedule: tuple[FixtureSpec, ...]
    results: tuple[GroupMatch, ...]
    sources: tuple[str, ...]
    stage_id: str | None = None
    group_id: str | None = None
    unknown_venues: frozenset[FixtureId] = frozenset()


@dataclass(frozen=True, slots=True)
class GroupEntry:
    competition_id: CompetitionId
    source_stage_id: str
    group_id: str
    position: int
    target_stage_id: str
    representative: ClubSeasonId


@dataclass(frozen=True, slots=True)
class PlayedMatch:
    fixture: SeasonFixture
    result: MatchResult


@dataclass(frozen=True, slots=True)
class RankedTable:
    snapshot: TableSnapshot
    unresolved: tuple[tuple[ClubSeasonId, ...], ...]


@dataclass(frozen=True, slots=True)
class Block:
    start: date
    end: date
    state_as_of: date
    managed_team: SimTeam
    references: tuple[SimTeam, ...]
    rivals: tuple[SimTeam, ...]
    competitions: tuple[Competition, ...]
    fixtures: tuple[SeasonFixture, ...]
    snapshots: tuple[TableSnapshot, ...]
    evidence: tuple[HistoricalEvidence, ...]
    priorities: dict[CompetitionId, Priority]
    injuries: tuple[Injury, ...]
    initial_absences: dict[PlayerId, date]
    youth: frozenset[PlayerId]
    prior: tuple[PlayedMatch, ...]
    slots: tuple[SeasonFixture, ...] = ()
    entries: tuple[GroupEntry, ...] = ()
    rival_absences: tuple[tuple[ClubSeasonId, PlayerId, date], ...] = ()


@dataclass(frozen=True, slots=True)
class PlayerState:
    player_id: PlayerId
    fitness: int
    injured_until: date | None
    minutes: int


@dataclass(frozen=True, slots=True)
class SeasonOutcome:
    results: tuple[PlayedMatch, ...]
    tables: tuple[RankedTable, ...]
    injuries: tuple[Injury, ...]
    states: tuple[PlayerState, ...]
    events: tuple[SeasonEvent, ...] = ()
    unresolved: tuple[KnockoutTie, ...] = ()


@dataclass(frozen=True, slots=True)
class SeasonEvent:
    kind: str
    date: date
    competition_id: CompetitionId
    stage_id: str | None


class SeasonSimulation:
    """One call owns mutable working copies; values entering and leaving remain immutable."""

    def __init__(self, block: Block, rng: RandomSource, simulator: MatchSimulator) -> None:
        self.block = block
        self.rng = rng
        self.simulator = simulator
        self.team = block.managed_team
        self.cursor = block.state_as_of
        self.injuries = list(block.injuries)
        self.new_injuries = [i for i in block.injuries if block.start <= i.date <= block.end]
        self.minutes = dict.fromkeys((p.player_id for p in self.team.squad or ()), 0)
        self.youth_available: set[PlayerId] = set()
        teams = {t.club_season_id: t for t in block.references}
        self.references = {
            c.competition_id: StrengthReference.from_teams(tuple(teams[p] for p in c.participants))
            for c in block.competitions
        }
        self.rivals = {t.club_season_id: t for t in (*block.references, *block.rivals)}
        self.competitions = {c.competition_id: c for c in block.competitions}
        self.played = {p.fixture.spec.fixture_id: p for p in block.prior}
        self.results: list[PlayedMatch] = []
        self.events: list[SeasonEvent] = []
        self.used_prior: set[object] = set()
        self.stage_maps: dict[tuple[CompetitionId, str], dict[ClubSeasonId, ClubSeasonId]] = {}
        self.closed_groups: set[tuple[CompetitionId, str]] = set()
        self._validate_evidence_consistency()
        self._validate_original_tables()
        self._validate_group_feeders()

    def _validate_evidence_consistency(self) -> None:
        fixtures: dict[FixtureId, FixtureSpec] = {}
        scores: dict[FixtureId, Score] = {}
        venues: dict[FixtureId, Venue] = {}
        for evidence in self.block.evidence:
            for fixture in evidence.schedule:
                previous = fixtures.get(fixture.fixture_id)
                if previous is not None and replace(previous, venue=fixture.venue) != fixture:
                    raise InvalidValueError(
                        "historical declarations contradict fixture identity or dates"
                    )
                fixtures[fixture.fixture_id] = fixture
                if fixture.fixture_id not in evidence.unknown_venues:
                    previous_venue = venues.get(fixture.fixture_id)
                    if previous_venue is not None and previous_venue is not fixture.venue:
                        raise InvalidValueError("historical declarations contradict a known venue")
                    venues[fixture.fixture_id] = fixture.venue
            for match in evidence.results:
                previous_score = scores.get(match.fixture.fixture_id)
                if previous_score is not None and previous_score != match.score:
                    raise InvalidValueError(
                        "historical declarations contradict the same fixture score"
                    )
                scores[match.fixture.fixture_id] = match.score
        self._resolve_known_venues(venues)

    def _resolve_known_venues(self, venues: dict[FixtureId, Venue]) -> None:
        declarations = []
        for evidence in self.block.evidence:
            completed = evidence.unknown_venues.intersection(venues)
            if not completed:
                declarations.append(evidence)
                continue
            fixtures = tuple(
                replace(f, venue=venues[f.fixture_id]) if f.fixture_id in completed else f
                for f in evidence.schedule
            )
            by_id = {f.fixture_id: f for f in fixtures}
            declarations.append(
                replace(
                    evidence,
                    schedule=fixtures,
                    results=tuple(
                        GroupMatch(by_id[m.fixture.fixture_id], m.score) for m in evidence.results
                    ),
                    unknown_venues=evidence.unknown_venues.difference(completed),
                )
            )
        self.block = replace(self.block, evidence=tuple(declarations))

    def _validate_group_feeders(self) -> None:
        for entry in self.block.entries:
            destinations = [
                f.spec.date
                for f in self.block.slots
                if (f.spec.competition_id, f.spec.stage)
                == (entry.competition_id, entry.target_stage_id)
                and entry.representative in (f.spec.home, f.spec.away)
            ]
            if not destinations:
                raise InvalidValueError("group entry has no destination fixture")
            destination = min(destinations)
            known = [
                f.date
                for e in self.block.evidence
                if (e.competition_id, e.stage_id, e.group_id)
                == (entry.competition_id, entry.source_stage_id, entry.group_id)
                for f in e.schedule
            ]
            known.extend(
                f.spec.date
                for f in self.block.fixtures
                if (f.spec.competition_id, f.spec.stage, f.spec.group)
                == (entry.competition_id, entry.source_stage_id, entry.group_id)
            )
            if any(day >= destination for day in known):
                raise InvalidValueError("group calendar must close before its knockout destination")
            if destination > self.block.end:
                continue
            competition = self.competitions[entry.competition_id]
            stage = next(s for s in competition.stages if s.stage_id == entry.source_stage_id)
            participants = next(clubs for group, clubs in stage.groups if group == entry.group_id)
            if not self._group_closed(
                competition, stage, entry.group_id, participants, destination - timedelta(days=1)
            ):
                raise InvalidValueError(
                    "missing group closure evidence before knockout destination"
                )

    def _validate_original_tables(self) -> None:
        for snapshot in self.block.snapshots:
            competition = self.competitions[snapshot.competition_id]
            stage = next((s for s in competition.stages if s.stage_id == snapshot.stage_id), None)
            rules = stage.group_rules if stage else None
            ppw = rules.points_per_win if rules else competition.points_per_win
            ppd = rules.points_per_draw if rules else competition.points_per_draw
            for evidence in self.block.evidence:
                if (evidence.competition_id, evidence.stage_id, evidence.group_id) != (
                    snapshot.competition_id,
                    snapshot.stage_id,
                    snapshot.group_id,
                ) or set(evidence.participants) != {r.club_season_id for r in snapshot.rows}:
                    continue
                if evidence.complete_through < snapshot.as_of and not self._complete_group_evidence(
                    evidence, snapshot.as_of
                ):
                    continue
                original = self._historical_rows(
                    evidence, evidence.participants, snapshot.as_of, ppw, ppd
                )
                if {r.club_season_id: r for r in original} != {
                    r.club_season_id: r for r in snapshot.rows
                }:
                    raise InvalidValueError(
                        "complete historical calendar contradicts original snapshot totals"
                    )

    def _absence(self, player_id: PlayerId, on_date: date) -> date | None:
        ends = [injured_until(player_id, tuple(self.injuries), on_date)]
        initial = self.block.initial_absences.get(player_id)
        if initial is not None and on_date < initial:
            ends.append(initial)
        return max((end for end in ends if end is not None), default=None)

    def _recover(self, on_date: date) -> None:
        self.team = replace(
            self.team,
            squad=tuple(
                replace(
                    p,
                    fitness=recover_between(p.fitness, self.cursor, on_date),
                    injured=self._absence(p.player_id, on_date) is not None,
                )
                for p in self.team.squad or ()
            ),
        )
        self.cursor = on_date

    def _youth_calendar(
        self, current: FixtureSpec, tie: KnockoutTie | None
    ) -> tuple[FixtureSpec, ...]:
        """Use fixed regular games and already accredited knockout participation.

        An undecided later knockout round is not a guaranteed opportunity for minutes.
        """
        fixtures = {current.fixture_id: current}
        for fixture in self.block.fixtures:
            if (
                fixture.spec.group is not None
                or self.competitions[fixture.spec.competition_id].kind == "league"
            ):
                fixtures[fixture.spec.fixture_id] = fixture.spec
        for fixture in self.block.slots:
            spec = fixture.spec
            competition = self.competitions[spec.competition_id]
            mapping = self.stage_maps.get((spec.competition_id, spec.stage or ""))
            if mapping is None and competition.stages[0].stage_id == spec.stage:
                mapping = {club: club for club in competition.participants}
            if mapping is not None and self.team.club_season_id in (
                mapping[spec.home],
                mapping[spec.away],
            ):
                fixtures[spec.fixture_id] = spec
        if tie is not None:
            fixtures.update((fixture.fixture_id, fixture) for fixture in tie.fixtures)
        return tuple(
            sorted(
                (
                    fixture
                    for fixture in fixtures.values()
                    if (fixture.date, str(fixture.fixture_id))
                    >= (current.date, str(current.fixture_id))
                    and fixture.date <= self.block.end
                    and fixture.fixture_id not in self.played
                ),
                key=lambda fixture: (fixture.date, str(fixture.fixture_id)),
            )
        )

    def _youth_required(self, current: FixtureSpec, tie: KnockoutTie | None) -> frozenset[PlayerId]:
        available = {player.player_id for player in self.team.squad or () if not player.injured}
        self.youth_available.update(self.block.youth & available)
        pending = tuple(
            sorted((player for player in self.block.youth if self.minutes[player] == 0), key=str)
        )
        ready = frozenset(player for player in pending if player in available)
        if len(ready) <= _STARTERS:
            return ready
        calendar = self._youth_calendar(current, tie)
        opportunities = {
            player: tuple(
                index
                for index, fixture in enumerate(calendar)
                if self._absence(player, fixture.date) is None
            )
            for player in pending
        }
        assignments: list[list[PlayerId]] = [[] for _ in calendar]

        def place(player: PlayerId, visited: set[int]) -> bool:
            eligible = tuple(index for index in opportunities[player] if index not in visited)
            for index in eligible:
                if len(assignments[index]) < _STARTERS:
                    assignments[index].append(player)
                    return True
            for index in eligible:
                visited.add(index)
                for occupant in reversed(assignments[index]):
                    if place(occupant, visited):
                        assignments[index].remove(occupant)
                        assignments[index].append(player)
                        return True
            return False

        for player in sorted(pending, key=lambda player: (len(opportunities[player]), str(player))):
            place(player, set())
        return frozenset(assignments[0])

    def _play(self, fixture: SeasonFixture, tie: KnockoutTie | None = None) -> PlayedMatch:
        spec = fixture.spec
        self._recover(spec.date)
        competition = self.competitions[spec.competition_id]
        priority = self.block.priorities.get(spec.competition_id, Priority.NORMAL)
        required = self._youth_required(spec, tie)
        squad = cast("tuple[SimPlayer, ...]", self.team.squad)
        tactic = cast("Tactic", self.team.tactic)
        lineup = select_lineup(squad, tactic, priority=priority, required=required)
        own = calculate_strength(self.team, self.references[spec.competition_id], lineup=lineup)
        rival_id = spec.away if spec.home == self.team.club_season_id else spec.home
        rival_team = self.rivals[rival_id]
        if rival_team.squad is not None:
            unavailable = {
                pid
                for club, pid, until in self.block.rival_absences
                if club == rival_id and spec.date < until
            }
            rival_team = replace(
                rival_team,
                squad=tuple(
                    replace(p, injured=p.player_id in unavailable) for p in rival_team.squad
                ),
            )
        rival = calculate_strength(rival_team, self.references[spec.competition_id], neutral=True)
        setup = MatchSetup(
            spec,
            own if spec.home == self.team.club_season_id else rival,
            rival if spec.home == self.team.club_season_id else own,
            competition.params,
        )
        result = (
            self.simulator.simulate(setup, self.rng, decisive=False)
            if tie is None
            else tie.play_next(setup, self.simulator, self.rng).results[-1]
        )
        if tie is None and (result.extra_time is not None or result.penalties is not None):
            raise InvalidValueError("league and group matches cannot have deciding periods")
        minutes = 120 if result.extra_time is not None else 90
        starters = {p.player.player_id for p in lineup.starters}
        players = []
        for p in squad:
            exposure = minutes if p.player_id in starters else 0
            injury = simulate_injury(
                self.rng,
                spec.fixture_id,
                p.player_id,
                spec.date,
                fitness=p.fitness,
                minutes=exposure,
            )
            if injury is not None:
                self.injuries.append(injury)
                self.new_injuries.append(injury)
            self.minutes[p.player_id] += exposure
            players.append(replace(p, fitness=match_fitness(p.fitness, exposure, priority)))
        self.team = replace(self.team, squad=tuple(players))
        played = PlayedMatch(fixture, result)
        self.played[spec.fixture_id] = played
        self.results.append(played)
        return played

    def _evidence(
        self,
        competition_id: CompetitionId,
        cutoff: date,
        stage_id: str | None = None,
        group_id: str | None = None,
    ) -> HistoricalEvidence | None:
        candidates = [
            e
            for e in self.block.evidence
            if (e.competition_id, e.stage_id, e.group_id) == (competition_id, stage_id, group_id)
            and (e.complete_through >= cutoff or self._complete_group_evidence(e, cutoff))
        ]
        return min(candidates, key=lambda e: e.complete_through, default=None)

    def _complete_group_evidence(self, evidence: HistoricalEvidence, cutoff: date) -> bool:
        if evidence.stage_id is None or evidence.group_id is None:
            return False
        competition = self.competitions[evidence.competition_id]
        stage = next(s for s in competition.stages if s.stage_id == evidence.stage_id)
        participants = next(clubs for group, clubs in stage.groups if group == evidence.group_id)
        if set(evidence.participants) != set(participants) or any(
            f.date > min(cutoff, evidence.complete_through) for f in evidence.schedule
        ):
            return False
        counts = {
            club: sum(club in (f.home, f.away) for f in evidence.schedule) for club in participants
        }
        return all(
            count == (len(participants) - 1) * stage.group_rounds for count in counts.values()
        )

    def _replacements(
        self,
        competition_id: CompetitionId,
        cutoff: date,
        stage_id: str | None = None,
        group_id: str | None = None,
    ) -> tuple[ResultReplacement, ...]:
        replacements = []
        for fixture in self.block.fixtures:
            spec = fixture.spec
            if (spec.competition_id, spec.stage, spec.group) != (
                competition_id,
                stage_id,
                group_id,
            ):
                continue
            if spec.date > cutoff:
                continue
            played = self.played.get(spec.fixture_id)
            if played is None or fixture.historical is None:
                raise InvalidValueError(
                    "missing prior result or historical score for P2 replacement"
                )
            replacements.append(
                ResultReplacement(
                    spec.fixture_id,
                    spec.date,
                    spec.home,
                    spec.away,
                    fixture.historical,
                    played.result.regulation,
                )
            )
        return tuple(replacements)

    def _baseline(
        self,
        competition: Competition,
        cutoff: date,
        participants: tuple[ClubSeasonId, ...],
        stage: Stage | None = None,
        group_id: str | None = None,
    ) -> tuple[TableSnapshot, tuple[ClubSeasonId, ...]]:
        snapshots = sorted(
            (
                s
                for s in self.block.snapshots
                if (s.competition_id, s.stage_id, s.group_id)
                == (competition.competition_id, stage.stage_id if stage else None, group_id)
            ),
            key=lambda s: s.as_of,
        )
        rounds = stage.knockout_rules.legs if stage and stage.knockout_rules else competition.rounds
        # Group legs denote round-robin repetitions and are kept separately from KO rules.
        if stage is not None:
            rounds = stage.group_rounds
        full_played = (len(participants) - 1) * (rounds or 1)
        candidates = [
            s
            for s in snapshots
            if s.as_of == cutoff
            or (s.as_of <= cutoff and all(r.played == full_played for r in s.rows))
        ]
        if candidates:
            return candidates[-1], snapshots[-1].order
        evidence = self._evidence(
            competition.competition_id, cutoff, stage.stage_id if stage else None, group_id
        )
        if evidence is None or set(evidence.participants) != set(participants):
            raise InvalidValueError("missing original historical standings at block cutoff")
        # A declared complete calendar can provide the original baseline at an arbitrary cutoff.
        rules = stage.group_rules if stage else None
        ppw = rules.points_per_win if rules else competition.points_per_win
        ppd = rules.points_per_draw if rules else competition.points_per_draw
        rows = self._historical_rows(evidence, participants, cutoff, ppw, ppd)
        return TableSnapshot(
            competition.competition_id,
            cutoff,
            rows,
            tuple(participants),
            stage.stage_id if stage else None,
            group_id,
        ), snapshots[-1].order if snapshots else ()

    @staticmethod
    def _historical_rows(
        evidence: HistoricalEvidence,
        participants: tuple[ClubSeasonId, ...],
        cutoff: date,
        ppw: int,
        ppd: int,
    ) -> tuple[LeagueRow, ...]:
        required = {f.fixture_id for f in evidence.schedule if f.date <= cutoff}
        matches = {m.fixture.fixture_id: m for m in evidence.results if m.fixture.date <= cutoff}
        if required != matches.keys():
            raise InvalidValueError("missing historical score in complete calendar")
        values = {club: [0] * 7 for club in participants}
        for match in matches.values():
            for club, gf, ga in (
                (match.fixture.home, match.score.home, match.score.away),
                (match.fixture.away, match.score.away, match.score.home),
            ):
                row = values[club]
                win, draw, loss = int(gf > ga), int(gf == ga), int(gf < ga)
                for i, amount in enumerate((1, win, draw, loss, gf, ga, win * ppw + draw * ppd)):
                    row[i] += amount
        return tuple(LeagueRow(club, *values[club]) for club in participants)

    def _table(self, competition: Competition) -> RankedTable:
        baseline, final_order = self._baseline(
            competition, self.block.end, competition.participants
        )
        if not final_order:
            raise InvalidValueError("league requires a separate original final historical order")
        request = ExternalResultsRequest(
            competition.competition_id,
            self.block.end,
            self.team.club_season_id,
            competition.participants,
            competition.points_per_win,
            competition.points_per_draw,
            baseline.rows,
            self._replacements(competition.competition_id, self.block.end),
        )
        original = self._evidence(competition.competition_id, self.block.end)
        evidence = None
        if original is not None:
            fixtures = tuple(f for f in original.schedule if f.date <= self.block.end)
            scores = {m.fixture.fixture_id: m.score for m in original.results}
            evidence = HeadToHeadEvidence(
                competition.competition_id,
                self.block.end,
                original.participants,
                tuple(
                    HeadToHeadFixture(
                        f.fixture_id,
                        f.date,
                        f.home,
                        f.away,
                        None if f.fixture_id in original.unknown_venues else f.venue,
                    )
                    for f in fixtures
                ),
                tuple(
                    HeadToHeadResult(
                        f.fixture_id, f.date, f.home, f.away, scores[f.fixture_id], original.sources
                    )
                    for f in fixtures
                ),
                original.sources,
            )
        table = LeagueTable(
            request,
            HistoricalExternalResults().standings(request),
            competition.tiebreakers,
            final_order,
            evidence,
        )
        historical_final = max(
            (
                s
                for s in self.block.snapshots
                if s.competition_id == competition.competition_id and s.stage_id is None
            ),
            key=lambda s: s.as_of,
        )
        unresolved = list(table.unresolved_groups)
        for tied in historical_final.unresolved_ties or ():
            for points in {r.points for r in table.rows if r.club_season_id in tied}:
                point_group = tuple(r.club_season_id for r in table.rows if r.points == points)
                remaining = tuple(club for club in point_group if club in tied)
                if len(remaining) > 1 and self.team.club_season_id not in point_group:
                    unresolved.append(remaining)
        ranked = RankedTable(
            replace(baseline, as_of=self.block.end, rows=table.rows), tuple(unresolved)
        )
        self._league_champion(competition, ranked, baseline.as_of)
        return ranked

    def _league_champion(
        self, competition: Competition, table: RankedTable, baseline_date: date
    ) -> None:
        rows = table.snapshot.rows
        full = (len(competition.participants) - 1) * (competition.rounds or 1)
        if (
            not all(r.played == full for r in rows)
            or rows[0].club_season_id != self.team.club_season_id
        ):
            return
        if any(self.team.club_season_id in tied for tied in table.unresolved):
            return
        evidence = self._evidence(competition.competition_id, self.block.end)
        close = (
            max((f.date for f in evidence.schedule), default=baseline_date)
            if evidence
            else baseline_date
        )
        if self.block.start <= close <= self.block.end:
            self.events.append(SeasonEvent("champion", close, competition.competition_id, None))

    def _group_table(
        self,
        competition: Competition,
        stage: Stage,
        group_id: str,
        participants: tuple[ClubSeasonId, ...],
        cutoff: date,
    ) -> tuple[RankedTable, tuple[ClubSeasonId, ...]]:
        rules = stage.group_rules
        if rules is None:
            raise InvalidValueError("group stage requires explicit group rules")
        baseline, _ = self._baseline(competition, cutoff, participants, stage, group_id)
        own_group = self.team.club_season_id in participants
        replacements = self._replacements(
            competition.competition_id, cutoff, stage.stage_id, group_id
        )
        # P2's replacement value includes the managed club; external groups retain original totals.
        rows = baseline.rows
        if own_group:
            request = ExternalResultsRequest(
                competition.competition_id,
                cutoff,
                self.team.club_season_id,
                participants,
                rules.points_per_win,
                rules.points_per_draw,
                baseline.rows,
                replacements,
            )
            rows = HistoricalExternalResults().standings(request)
        original = self._evidence(competition.competition_id, cutoff, stage.stage_id, group_id)
        evidence = None
        if original is not None:
            simulated = {r.fixture_id: r.simulated_score for r in replacements}
            results = tuple(
                GroupMatch(m.fixture, simulated.get(m.fixture.fixture_id, m.score))
                for m in original.results
                if m.fixture.date <= cutoff
            )
            evidence = GroupEvidence(cutoff, original.schedule, results)
        table = GroupTable(
            competition.competition_id,
            stage.stage_id,
            group_id,
            participants,
            rows,
            rules,
            evidence,
        )
        if original is not None and original.unknown_venues:
            self._require_group_venues(table, original, cutoff)
        ranking = table.rank()
        # Qualifier evaluation is deferred until closure, preserving intermediate unresolved tables.
        return RankedTable(
            replace(baseline, as_of=cutoff, rows=ranking.rows), ranking.unresolved_ties
        ), ranking.qualifiers if self._group_closed(
            competition, stage, group_id, participants, cutoff
        ) else ()

    @staticmethod
    def _require_group_venues(
        table: GroupTable, original: HistoricalEvidence, cutoff: date
    ) -> None:
        """Validate venues only when ranking reaches the away-goal criterion.

        Mini-table counters are computed together by the ranking strategy. This traversal
        preserves its original tied sets, criterion order and reapplication while checking
        provenance only at the criterion that actually depends on the venue.
        """
        rows = {row.club_season_id: row for row in table.rows}
        criteria = table.rules.tiebreakers
        coefficients = dict(table.rules.coefficients)

        def resolve(members: tuple[ClubSeasonId, ...], index: int) -> None:
            if len(members) <= 1 or index == len(criteria):
                return
            if not criteria[index].startswith("head_to_head_"):
                for part in _partition(
                    members, lambda club: _overall_value(rows[club], criteria[index], coefficients)
                ):
                    resolve(part, index + 1)
                return
            end = index
            while end < len(criteria) and criteria[end].startswith("head_to_head_"):
                end += 1
            values = table._mini_table(members)
            partitions: tuple[tuple[ClubSeasonId, ...], ...] = (members,)
            for criterion in criteria[index:end]:
                if (
                    criterion == "head_to_head_away_goals"
                    and any(len(part) > 1 for part in partitions)
                    and any(
                        f.fixture_id in original.unknown_venues
                        and f.date <= cutoff
                        and f.home in members
                        and f.away in members
                        for f in original.schedule
                    )
                ):
                    raise InvalidValueError("group away-goal criterion requires known venues")
                criterion_values = {club: values[club][criterion] for club in members}
                partitions = tuple(
                    part
                    for group in partitions
                    for part in _partition(group, criterion_values.__getitem__)
                )
            for part in partitions:
                resolve(
                    part,
                    index
                    if table.rules.reapply_head_to_head
                    and len(partitions) > 1
                    and len(part) == _TWO_CLUBS
                    else end,
                )

        for members in _partition(table.participants, lambda club: rows[club].points):
            resolve(members, 0)

    def _group_closed(
        self,
        competition: Competition,
        stage: Stage,
        group_id: str,
        participants: tuple[ClubSeasonId, ...],
        cutoff: date,
    ) -> bool:
        full = (len(participants) - 1) * stage.group_rounds
        evidence = self._evidence(competition.competition_id, cutoff, stage.stage_id, group_id)
        if evidence is not None and set(evidence.participants) == set(participants):
            if any(f.date > cutoff for f in evidence.schedule):
                return False
            rows = self._historical_rows(
                evidence,
                participants,
                cutoff,
                stage.group_rules.points_per_win if stage.group_rules else 0,
                stage.group_rules.points_per_draw if stage.group_rules else 0,
            )
            return all(r.played == full for r in rows)
        return any(
            s.competition_id == competition.competition_id
            and s.stage_id == stage.stage_id
            and s.group_id == group_id
            and s.as_of <= cutoff
            and all(r.played == full for r in s.rows)
            for s in self.block.snapshots
        )

    def _close_groups(self, competition: Competition, stage: Stage, cutoff: date) -> None:
        key = competition.competition_id, stage.stage_id
        if key in self.closed_groups:
            return
        for group_id, participants in stage.groups:
            if self.team.club_season_id not in participants or not self._group_closed(
                competition, stage, group_id, participants, cutoff
            ):
                continue
            _, qualifiers = self._group_table(competition, stage, group_id, participants, cutoff)
            evidence = self._evidence(competition.competition_id, cutoff, stage.stage_id, group_id)
            close = (
                max((f.date for f in evidence.schedule), default=cutoff)
                if evidence
                else min(
                    s.as_of
                    for s in self.block.snapshots
                    if s.competition_id == competition.competition_id
                    and s.stage_id == stage.stage_id
                    and s.group_id == group_id
                    and all(
                        r.played == (len(participants) - 1) * stage.group_rounds for r in s.rows
                    )
                )
            )
            if self.block.start <= close <= self.block.end:
                self.events.append(
                    SeasonEvent(
                        "advanced" if self.team.club_season_id in qualifiers else "eliminated",
                        close,
                        competition.competition_id,
                        stage.stage_id,
                    )
                )
            self.closed_groups.add(key)

    def _group_mapping(
        self,
        competition: Competition,
        previous: Stage,
        stage: Stage,
    ) -> dict[ClubSeasonId, ClubSeasonId] | None:
        mapping = {}
        entries = [
            e
            for e in self.block.entries
            if e.competition_id == competition.competition_id
            and e.source_stage_id == previous.stage_id
            and e.target_stage_id == stage.stage_id
        ]
        for group_id, participants in previous.groups:
            if not self._group_closed(
                competition, previous, group_id, participants, self.block.end
            ):
                return None
            ranked, qualifiers = self._group_table(
                competition, previous, group_id, participants, self.block.end
            )
            if any(set(tied).intersection(qualifiers) for tied in ranked.unresolved):
                raise InvalidValueError("unresolved group positions cannot select knockout slots")
            for entry in (e for e in entries if e.group_id == group_id):
                mapping[entry.representative] = qualifiers[entry.position - 1]
        if not mapping or len(set(mapping.values())) != len(mapping):
            raise InvalidValueError("group entry assignments must form a complete bijection")
        self._close_groups(competition, previous, self.block.end)
        return mapping

    def _knockout_mapping(
        self,
        competition: Competition,
        previous: Stage,
    ) -> dict[ClubSeasonId, ClubSeasonId] | None:
        mapping = {}
        previous_map = self._mapping(competition, previous)
        if previous_map is None:
            return None
        for historical in (t for t in competition.ties if t.stage_id == previous.stage_id):
            if historical.winner is None:
                raise InvalidValueError(
                    "progression requires a known historical winning representative"
                )
            effective = tuple(previous_map[c] for c in historical.clubs)
            if self.team.club_season_id in effective:
                tie = self._tie(competition, previous, historical, previous_map)
                if tie.winner is None:
                    return None
                mapping[historical.winner] = tie.winner
            else:
                mapping[historical.winner] = previous_map[historical.winner]
        return mapping

    def _mapping(
        self, competition: Competition, stage: Stage
    ) -> dict[ClubSeasonId, ClubSeasonId] | None:
        key = competition.competition_id, stage.stage_id
        if key in self.stage_maps:
            return self.stage_maps[key]
        index = competition.stages.index(stage)
        if index == 0:
            mapping = {p: p for p in competition.participants}
        else:
            previous = competition.stages[index - 1]
            mapping = {}
            resolved = (
                self._group_mapping(competition, previous, stage)
                if previous.groups
                else self._knockout_mapping(competition, previous)
            )
            if resolved is None:
                return None
            mapping = resolved
            expected = {
                club for t in competition.ties if t.stage_id == stage.stage_id for club in t.clubs
            }
            if set(mapping) != expected or len(set(mapping.values())) != len(mapping):
                raise InvalidValueError(
                    "historical feeders must exactly cover the next stage's slots"
                )
        self.stage_maps[key] = mapping
        return mapping

    def _tie(
        self,
        competition: Competition,
        stage: Stage,
        historical: HistoricalTie,
        mapping: dict[ClubSeasonId, ClubSeasonId],
    ) -> KnockoutTie:
        fixtures = tuple(
            replace(f.spec, home=mapping[f.spec.home], away=mapping[f.spec.away], key=True)
            for f in sorted(self.block.slots, key=lambda f: (f.spec.date, str(f.spec.fixture_id)))
            if f.spec.competition_id == competition.competition_id
            and f.spec.stage == stage.stage_id
            and {f.spec.home, f.spec.away} == set(historical.clubs)
        )
        if stage.knockout_rules is None:
            raise InvalidValueError("a knockout stage requires knockout rules")
        results = []
        for fixture in fixtures:
            played = self.played.get(fixture.fixture_id)
            if played is None:
                break
            if played.fixture.spec != fixture:
                raise InvalidValueError("prior result contradicts its effective knockout slot")
            results.append(played.result)
        return KnockoutTie(stage.knockout_rules, fixtures, tuple(results))

    def _consume(self, fixture: SeasonFixture, tie: KnockoutTie | None = None) -> None:
        spec = fixture.spec
        if spec.date < self.block.start:
            prior = self.played.get(spec.fixture_id)
            if prior is None or prior.fixture != fixture:
                raise InvalidValueError("missing or incoherent prior result in continuation gap")
            if tie is None and (
                prior.result.extra_time is not None or prior.result.penalties is not None
            ):
                raise InvalidValueError("league and group matches cannot have deciding periods")
            self.used_prior.add(spec.fixture_id)
            return
        self._play(fixture, tie)

    def _process_knockout(self, fixture: SeasonFixture, competition: Competition) -> None:
        spec = fixture.spec
        stage = next(s for s in competition.stages if s.stage_id == spec.stage)
        mapping = self._mapping(competition, stage)
        if mapping is None:
            return
        effective = replace(spec, home=mapping[spec.home], away=mapping[spec.away], key=True)
        if self.team.club_season_id not in (effective.home, effective.away):
            return
        historical = next(
            t
            for t in competition.ties
            if t.stage_id == stage.stage_id and set(t.clubs) == {spec.home, spec.away}
        )
        tie = self._tie(competition, stage, historical, mapping)
        current = SeasonFixture(effective, fixture.round, fixture.historical)
        self._consume(current, tie)
        if spec.date >= self.block.start:
            completed = self._tie(competition, stage, historical, mapping)
            if completed.winner is not None:
                kind = (
                    "eliminated"
                    if completed.winner != self.team.club_season_id
                    else ("champion" if stage.round == "final" else "advanced")
                )
                self.events.append(
                    SeasonEvent(kind, spec.date, competition.competition_id, stage.stage_id)
                )

    def _tables_and_unresolved(self) -> tuple[tuple[RankedTable, ...], tuple[KnockoutTie, ...]]:
        tables = []
        unresolved = []
        for competition in self.block.competitions:
            if competition.kind == "league":
                tables.append(self._table(competition))
            for stage in competition.stages:
                for group_id, participants in stage.groups:
                    if self.team.club_season_id in participants:
                        tables.append(
                            self._group_table(
                                competition, stage, group_id, participants, self.block.end
                            )[0]
                        )
                if stage.groups:
                    self._close_groups(competition, stage, self.block.end)
                    continue
                mapping = self._mapping(competition, stage)
                if mapping is None:
                    continue
                for historical in (t for t in competition.ties if t.stage_id == stage.stage_id):
                    if self.team.club_season_id not in (mapping[c] for c in historical.clubs):
                        continue
                    tie = self._tie(competition, stage, historical, mapping)
                    if len(tie.results) == tie.rules.legs and tie.winner is None:
                        unresolved.append(tie)
        return tuple(tables), tuple(unresolved)

    def run(self) -> SeasonOutcome:
        regular = tuple(
            f
            for f in self.block.fixtures
            if f.spec.group is not None or self.competitions[f.spec.competition_id].kind == "league"
        )
        schedule = sorted(
            (*regular, *self.block.slots), key=lambda f: (f.spec.date, str(f.spec.fixture_id))
        )
        for fixture in schedule:
            spec = fixture.spec
            if spec.date > self.block.end:
                continue
            competition = self.competitions[spec.competition_id]
            if fixture in regular:
                self._consume(fixture)
                continue
            self._process_knockout(fixture, competition)
        if self.used_prior != {p.fixture.spec.fixture_id for p in self.block.prior}:
            raise InvalidValueError("prior results include an inactive or unexpected fixture")
        if any(self.minutes[player] == 0 for player in self.youth_available):
            raise InvalidValueError(
                "youth participation requirements exceed the block's available minutes"
            )
        self._recover(self.block.end)
        tables, unresolved = self._tables_and_unresolved()
        return SeasonOutcome(
            tuple(self.results),
            tuple(tables),
            tuple(
                sorted(
                    self.new_injuries, key=lambda i: (i.date, str(i.player_id), i.forced, i.days)
                )
            ),
            tuple(
                PlayerState(
                    p.player_id,
                    p.fitness.value,
                    self._absence(p.player_id, self.block.end),
                    self.minutes[p.player_id],
                )
                for p in self.team.squad or ()
            ),
            tuple(
                sorted(self.events, key=lambda e: (e.date, str(e.competition_id), e.stage_id or ""))
            ),
            tuple(unresolved),
        )
