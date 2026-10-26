"""Pure chronological block coordination, retaining original P2 and strength references."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from typing import TYPE_CHECKING

from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import ClubSeasonId, CompetitionId, PlayerId
from mister.simulation.domain.fitness import match_fitness, recover_between
from mister.simulation.domain.injuries import Injury, injured_until, simulate_injury
from mister.simulation.domain.league import (
    HeadToHeadEvidence,
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

if TYPE_CHECKING:
    from mister.shared_kernel.randomness import RandomSource
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
    evidence: tuple[HeadToHeadEvidence, ...]
    priorities: dict[CompetitionId, Priority]
    injuries: tuple[Injury, ...]
    initial_absences: dict[PlayerId, date]
    youth: frozenset[PlayerId]
    prior: tuple[PlayedMatch, ...]


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
        teams = {t.club_season_id: t for t in block.references}
        self.references = {
            c.competition_id: StrengthReference.from_teams(tuple(teams[p] for p in c.participants))
            for c in block.competitions
        }
        self.rivals = {t.club_season_id: t for t in (*block.references, *block.rivals)}
        self.competitions = {c.competition_id: c for c in block.competitions}
        self.played = {p.fixture.spec.fixture_id: p for p in block.prior}
        self.results: list[PlayedMatch] = []

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

    def _play(self, fixture: SeasonFixture) -> PlayedMatch:
        spec = fixture.spec
        self._recover(spec.date)
        competition = self.competitions[spec.competition_id]
        priority = self.block.priorities.get(spec.competition_id, Priority.NORMAL)
        available = {p.player_id for p in self.team.squad or () if not p.injured}
        required = frozenset(p for p in self.block.youth & available if self.minutes[p] == 0)
        assert self.team.squad is not None and self.team.tactic is not None
        lineup = select_lineup(
            self.team.squad, self.team.tactic, priority=priority, required=required
        )
        own = calculate_strength(self.team, self.references[spec.competition_id], lineup=lineup)
        rival_id = spec.away if spec.home == self.team.club_season_id else spec.home
        rival = calculate_strength(
            self.rivals[rival_id], self.references[spec.competition_id], neutral=True
        )
        setup = MatchSetup(
            spec,
            own if spec.home == self.team.club_season_id else rival,
            rival if spec.home == self.team.club_season_id else own,
            competition.params,
        )
        result = self.simulator.simulate(setup, self.rng, decisive=False)
        minutes = 120 if result.extra_time is not None else 90
        starters = {p.player.player_id for p in lineup.starters}
        players = []
        for p in self.team.squad:
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

    def _table(self, competition: Competition) -> RankedTable:
        snapshots = sorted(
            (
                s
                for s in self.block.snapshots
                if s.competition_id == competition.competition_id and s.stage_id is None
            ),
            key=lambda s: s.as_of,
        )
        candidates = [
            s
            for s in snapshots
            if s.as_of == self.block.end
            or (
                s.as_of <= self.block.end
                and competition.rounds is not None
                and all(
                    r.played == (len(competition.participants) - 1) * competition.rounds
                    for r in s.rows
                )
            )
        ]
        if not candidates:
            raise InvalidValueError("missing original historical standings at block cutoff")
        baseline = candidates[-1]
        replacements = []
        for fixture in self.block.fixtures:
            spec = fixture.spec
            if spec.competition_id != competition.competition_id or spec.date > self.block.end:
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
        request = ExternalResultsRequest(
            competition.competition_id,
            self.block.end,
            self.team.club_season_id,
            competition.participants,
            competition.points_per_win,
            competition.points_per_draw,
            baseline.rows,
            tuple(replacements),
        )
        evidence = next(
            (
                e
                for e in self.block.evidence
                if e.competition_id == competition.competition_id and e.as_of == self.block.end
            ),
            None,
        )
        table = LeagueTable(
            request,
            HistoricalExternalResults().standings(request),
            competition.tiebreakers,
            snapshots[-1].order,
            evidence,
        )
        return RankedTable(
            replace(baseline, as_of=self.block.end, rows=table.rows), table.unresolved_groups
        )

    def run(self) -> SeasonOutcome:
        for fixture in sorted(
            self.block.fixtures, key=lambda f: (f.spec.date, str(f.spec.fixture_id))
        ):
            spec = fixture.spec
            if spec.date < self.block.start:
                if spec.fixture_id not in self.played:
                    raise InvalidValueError("missing prior result in continuation gap")
            elif spec.date <= self.block.end:
                self._play(fixture)
        self._recover(self.block.end)
        return SeasonOutcome(
            tuple(self.results),
            tuple(self._table(c) for c in self.block.competitions if c.kind == "league"),
            tuple(self.new_injuries),
            tuple(
                PlayerState(
                    p.player_id,
                    p.fitness.value,
                    self._absence(p.player_id, self.block.end),
                    self.minutes[p.player_id],
                )
                for p in self.team.squad or ()
            ),
        )
