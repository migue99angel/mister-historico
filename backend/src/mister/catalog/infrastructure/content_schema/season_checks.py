"""Referential and consistency checks for one playable season."""

from collections import Counter
from dataclasses import dataclass
from datetime import date

from mister.catalog.infrastructure.content_schema.effects import (
    CompetitionPriorityEffect,
    Effect,
    FitnessEffect,
    InjuryEffect,
    PlayerMoraleEffect,
    SellPlayerEffect,
    SignPlayerEffect,
    YouthMinutesEffect,
)
from mister.catalog.infrastructure.content_schema.fixtures import Fixture
from mister.catalog.infrastructure.content_schema.integrity import squad_path
from mister.catalog.infrastructure.content_schema.issues import IssueSink
from mister.catalog.infrastructure.content_schema.season import (
    Block,
    Competition,
    LeagueCompetition,
)
from mister.catalog.infrastructure.content_schema.tree import ContentTree, SeasonContent

DOUBLE_ROUND_ROBIN = 2
MIN_DILEMMAS_PER_BLOCK = 1
MAX_DILEMMAS_PER_BLOCK = 3
MIN_DILEMMAS = 8
MAX_DILEMMAS = 12


@dataclass(frozen=True)
class _Known:
    """Which club-season slugs exist, even if their file failed to load (no cascading errors)."""

    tree: ContentTree
    failed: frozenset[str]

    def exists(self, slug: str) -> bool:
        return slug in self.tree.club_season_ids or slug in self.failed

    def has_squad(self, slug: str) -> bool:
        return slug in self.tree.squads or slug in self.failed


class SeasonChecker:
    """Runs every integrity rule of one season and reports them to the sink."""

    def __init__(
        self,
        tree: ContentTree,
        failed_club_seasons: set[str],
        slug: str,
        sink: IssueSink,
    ) -> None:
        self._tree = tree
        self._known = _Known(tree, frozenset(failed_club_seasons))
        self._content: SeasonContent = tree.seasons[slug]
        self._base = f"seasons/{slug}"
        self._sink = sink
        season = self._content.season
        self._own = season.club_season
        self._blocks = season.blocks
        self._competitions = {c.id: c for c in season.competitions}
        own_squad = tree.squads.get(self._own)
        self._own_players = {p.player_id for p in own_squad.players} if own_squad else set()

    def _add(self, file: str, field: str, message: str) -> None:
        self._sink.add(f"{self._base}/{file}.yaml", field, message)

    def run(self) -> None:
        if not self._check_own_squad():
            return
        self._check_competitions()
        self._check_outcomes_and_objectives()
        self._check_fixtures()
        self._check_standings()
        self._check_dilemmas()

    # ------------------------------------------------------------------ season.yaml
    def _check_own_squad(self) -> bool:
        if self._own in self._tree.squads:
            return True
        if self._own not in self._known.failed:
            self._add("season", "club_season", f"{self._own!r} must be a club-season with a squad")
        return False

    def _check_competitions(self) -> None:
        for ci, competition in enumerate(self._content.season.competitions):
            for pi, participant in enumerate(competition.participants):
                field = f"competitions.{ci}.participants.{pi}"
                if not self._known.exists(participant) or participant.startswith("_market-"):
                    self._add("season", field, f"unknown club-season {participant!r}")
                elif isinstance(competition, LeagueCompetition) and not self._known.has_squad(
                    participant
                ):
                    self._add(
                        "season", field, f"league participant {participant!r} needs a squad.yaml"
                    )

    def _check_outcomes_and_objectives(self) -> None:
        seen: Counter[str] = Counter()
        for index, outcome in enumerate(self._content.season.historical_outcome):
            seen[outcome.competition] += 1
            field = f"historical_outcome.{index}"
            competition = self._competitions.get(outcome.competition)
            if competition is None:
                self._add(
                    "season", f"{field}.competition", f"unknown competition {outcome.competition!r}"
                )
                continue
            self._check_outcome(field, competition, index)
        for competition_id in self._competitions:
            if seen[competition_id] != 1:
                self._add(
                    "season",
                    "historical_outcome",
                    f"competition {competition_id!r} needs exactly one outcome, "
                    f"found {seen[competition_id]}",
                )
        for index, objective in enumerate(self._content.season.board_objectives):
            if objective.competition not in self._competitions:
                self._add(
                    "season",
                    f"board_objectives.{index}.competition",
                    f"unknown competition {objective.competition!r}",
                )

    def _check_outcome(self, field: str, competition: Competition, index: int) -> None:
        outcome = self._content.season.historical_outcome[index]
        if isinstance(competition, LeagueCompetition):
            if outcome.final_position is None and outcome.verify == "ok":
                self._add(
                    "season", f"{field}.final_position", "a league outcome needs final_position"
                )
            if outcome.eliminated_in is not None:
                self._add("season", f"{field}.eliminated_in", "a league has no elimination stage")
            return
        if outcome.final_position is not None:
            self._add("season", f"{field}.final_position", "final_position only applies to leagues")
        stages = {s.id for s in competition.stages}
        if outcome.eliminated_in is not None and outcome.eliminated_in not in stages:
            self._add(
                "season", f"{field}.eliminated_in", f"unknown stage {outcome.eliminated_in!r}"
            )

    # ------------------------------------------------------------------ fixtures.yaml
    def _block_of(self, day: date) -> Block | None:
        return next((b for b in self._blocks if b.start <= day <= b.end), None)

    def _check_fixtures(self) -> None:
        for index, fixture in enumerate(self._content.fixtures.fixtures):
            field = f"fixtures.{index}"
            competition = self._competitions.get(fixture.competition)
            if competition is None:
                self._add(
                    "fixtures",
                    f"{field}.competition",
                    f"unknown competition {fixture.competition!r}",
                )
                continue
            self._check_fixture_opponent(field, fixture.opponent, competition)
            if self._block_of(fixture.date) is None:
                self._add("fixtures", f"{field}.date", f"{fixture.date} falls outside every block")
            self._check_fixture_shape(field, index, competition)
        for competition in self._content.season.competitions:
            if isinstance(competition, LeagueCompetition):
                self._check_league_completeness(competition)

    def _check_fixture_opponent(self, field: str, opponent: str, competition: Competition) -> None:
        if not self._known.exists(opponent):
            self._add("fixtures", f"{field}.opponent", f"unknown club-season {opponent!r}")
        elif opponent == self._own:
            self._add("fixtures", f"{field}.opponent", "the opponent cannot be the own team")
        elif opponent not in competition.participants:
            self._add(
                "fixtures",
                f"{field}.opponent",
                f"{opponent!r} is not a participant of {competition.id!r}",
            )

    def _check_fixture_shape(self, field: str, index: int, competition: Competition) -> None:
        fixture = self._content.fixtures.fixtures[index]
        if isinstance(competition, LeagueCompetition):
            if fixture.round is None:
                self._add("fixtures", f"{field}.round", "a league fixture needs a round")
            elif fixture.round > (len(competition.participants) - 1) * competition.rounds:
                self._add(
                    "fixtures", f"{field}.round", f"round {fixture.round} is beyond the last round"
                )
            if fixture.venue == "neutral":
                self._add("fixtures", f"{field}.venue", "a league match is never on neutral ground")
            return
        if fixture.stage is None:
            group_stage = getattr(competition, "group_stage", None)
            if group_stage is None:
                self._add("fixtures", f"{field}.stage", "a knockout fixture needs a stage")
            return
        stage = next((s for s in competition.stages if s.id == fixture.stage), None)
        if stage is None:
            self._add("fixtures", f"{field}.stage", f"unknown stage {fixture.stage!r}")
        elif (fixture.leg or 1) > stage.legs:
            self._add("fixtures", f"{field}.leg", f"stage {stage.id!r} has {stage.legs} leg(s)")
        elif fixture.venue == "neutral" and stage.legs == DOUBLE_ROUND_ROBIN:
            self._add("fixtures", f"{field}.venue", "a two-legged tie is never on neutral ground")

    def _check_league_completeness(self, competition: LeagueCompetition) -> None:
        own = [f for f in self._content.fixtures.fixtures if f.competition == competition.id]
        expected = (len(competition.participants) - 1) * competition.rounds
        if len(own) != expected:
            self._add(
                "fixtures",
                "fixtures",
                f"{competition.id}: expected {expected} fixtures of the own team, found {len(own)}",
            )
        rounds = Counter(f.round for f in own if f.round is not None)
        for number, count in rounds.items():
            if count > 1:
                self._add("fixtures", "fixtures", f"{competition.id}: round {number} appears twice")
        for opponent in competition.participants:
            if opponent == self._own:
                continue
            venues = sorted(f.venue for f in own if f.opponent == opponent)
            if competition.rounds == DOUBLE_ROUND_ROBIN:
                valid, what = venues == ["away", "home"], "once at home and once away"
            else:
                valid, what = len(venues) == 1, "exactly once"
            if not valid:
                self._add(
                    "fixtures", "fixtures", f"{competition.id}: {opponent} must be met {what}"
                )

    # ------------------------------------------------------------------ standings.yaml
    def _check_standings(self) -> None:
        standings = self._content.standings
        blocks = {b.id: b for b in self._blocks}
        leagues = {c.id: c for c in self._competitions.values() if isinstance(c, LeagueCompetition)}
        present = {(c.block, c.competition) for c in standings.cutoffs}
        for block in self._blocks:
            for league_id in leagues:
                if (block.id, league_id) not in present:
                    self._add(
                        "standings",
                        "cutoffs",
                        f"missing cutoff for block {block.id} and {league_id}",
                    )
        for index, cutoff in enumerate(standings.cutoffs):
            field = f"cutoffs.{index}"
            cutoff_block, league = blocks.get(cutoff.block), leagues.get(cutoff.competition)
            if cutoff_block is None:
                self._add("standings", f"{field}.block", f"unknown block {cutoff.block!r}")
            elif cutoff.date != cutoff_block.end:
                self._add(
                    "standings",
                    f"{field}.date",
                    f"must be the end of block {cutoff_block.id} ({cutoff_block.end})",
                )
            if league is None:
                self._add(
                    "standings", f"{field}.competition", f"{cutoff.competition!r} is not a league"
                )
                continue
            self._check_table(field, index, league)
        self._check_ties()
        self._check_final_goals(leagues)

    def _check_table(self, field: str, index: int, league: LeagueCompetition) -> None:
        cutoff = self._content.standings.cutoffs[index]
        listed = {row.club_season for row in cutoff.table}
        expected = set(league.participants)
        if listed != expected:
            self._add(
                "standings",
                f"{field}.table",
                "the table must list exactly the participants of the competition "
                f"(missing: {sorted(expected - listed)}, unexpected: {sorted(listed - expected)})",
            )
        own_fixtures = [
            f
            for f in self._content.fixtures.fixtures
            if f.competition == league.id and f.date <= cutoff.date
        ]
        for row_index, row in enumerate(cutoff.table):
            row_field = f"{field}.table.{row_index}"
            wanted = row.won * league.points_per_win + row.drawn * league.points_per_draw
            if row.points != wanted:
                self._add("standings", f"{row_field}.points", f"expected {wanted} points")
            if row.club_season == self._own:
                self._check_own_row(row_field, row_index, index, own_fixtures)

    def _check_own_row(
        self, field: str, row_index: int, index: int, fixtures: list[Fixture]
    ) -> None:
        row = self._content.standings.cutoffs[index].table[row_index]
        results = [f.result for f in fixtures]
        if any(r is None for r in results):
            return  # a pending result cannot be compared
        won = sum(1 for r in results if r and r.goals_for > r.goals_against)
        drawn = sum(1 for r in results if r and r.goals_for == r.goals_against)
        actual = (
            len(results),
            won,
            drawn,
            len(results) - won - drawn,
            sum(r.goals_for for r in results if r),
            sum(r.goals_against for r in results if r),
        )
        stated = (row.played, row.won, row.drawn, row.lost, row.goals_for, row.goals_against)
        if actual != stated:
            self._add(
                "standings",
                field,
                "the own row does not match the own fixtures "
                f"(played, won, drawn, lost, gf, ga): table {stated}, fixtures {actual}",
            )

    def _check_ties(self) -> None:
        for index, tie in enumerate(self._content.standings.ties):
            field = f"ties.{index}"
            competition = self._competitions.get(tie.competition)
            if competition is None or isinstance(competition, LeagueCompetition):
                self._add(
                    "standings",
                    f"{field}.competition",
                    f"{tie.competition!r} is not a knockout competition",
                )
                continue
            if tie.stage not in {s.id for s in competition.stages}:
                self._add("standings", f"{field}.stage", f"unknown stage {tie.stage!r}")
            for club in tie.clubs:
                if club not in competition.participants:
                    self._add(
                        "standings",
                        f"{field}.clubs",
                        f"{club!r} is not a participant of {competition.id!r}",
                    )

    def _check_final_goals(self, leagues: dict[str, LeagueCompetition]) -> None:
        """The squad's real league goals must equal the last real table of the season."""
        for league in leagues.values():
            cutoffs = [c for c in self._content.standings.cutoffs if c.competition == league.id]
            if not cutoffs:
                continue
            final = max(cutoffs, key=lambda c: c.date)
            total = (len(league.participants) - 1) * league.rounds
            for row in final.table:
                squad = self._tree.squads.get(row.club_season)
                if squad is None or row.played != total:
                    continue
                for name, value in (
                    ("real_goals_for", row.goals_for),
                    ("real_goals_against", row.goals_against),
                ):
                    stated = getattr(squad, name)
                    if stated is not None and stated != value:
                        self._sink.add(
                            squad_path(row.club_season),
                            name,
                            f"{stated} differs from the final real standings ({value}) in "
                            f"{self._base}/standings.yaml",
                        )

    # ------------------------------------------------------------------ dilemmas.yaml
    def _check_dilemmas(self) -> None:
        dilemmas = self._content.dilemmas.dilemmas
        block_ids = {b.id for b in self._blocks}
        per_block = Counter(d.block for d in dilemmas)
        for index, dilemma in enumerate(dilemmas):
            if dilemma.block not in block_ids:
                self._add("dilemmas", f"dilemmas.{index}.block", f"unknown block {dilemma.block!r}")
        for block in self._blocks:
            count = per_block[block.id]
            if not MIN_DILEMMAS_PER_BLOCK <= count <= MAX_DILEMMAS_PER_BLOCK:
                self._add(
                    "dilemmas",
                    "dilemmas",
                    f"block {block.id} has {count} dilemmas; expected between "
                    f"{MIN_DILEMMAS_PER_BLOCK} and {MAX_DILEMMAS_PER_BLOCK}",
                )
        if not MIN_DILEMMAS <= len(dilemmas) <= MAX_DILEMMAS:
            self._add(
                "dilemmas",
                "dilemmas",
                f"{len(dilemmas)} dilemmas in total; "
                f"expected between {MIN_DILEMMAS} and {MAX_DILEMMAS}",
            )
        signed = {
            e.player_id
            for d in dilemmas
            for o in d.options
            for e in o.effects
            if isinstance(e, SignPlayerEffect)
        }
        usable = self._own_players | signed
        for di, dilemma in enumerate(dilemmas):
            for oi, option in enumerate(dilemma.options):
                for ei, effect in enumerate(option.effects):
                    self._check_effect(f"dilemmas.{di}.options.{oi}.effects.{ei}", effect, usable)

    def _check_effect(self, field: str, effect: Effect, usable: set[str]) -> None:
        match effect:
            case SignPlayerEffect():
                self._check_sign(field, effect)
            case SellPlayerEffect():
                self._check_player(f"{field}.player_id", effect.player_id, usable)
                if effect.to_club_season is not None:
                    self._check_squad_ref(f"{field}.to_club_season", effect.to_club_season)
            case PlayerMoraleEffect() | YouthMinutesEffect() | InjuryEffect():
                self._check_player(f"{field}.player_id", effect.player_id, usable)
                if isinstance(effect, InjuryEffect):
                    self._check_injury_date(field, effect.date)
            case FitnessEffect() if effect.player_id is not None:
                self._check_player(f"{field}.player_id", effect.player_id, usable)
            case CompetitionPriorityEffect():
                if effect.competition_id not in self._competitions:
                    self._add(
                        "dilemmas",
                        f"{field}.competition_id",
                        f"unknown competition {effect.competition_id!r}",
                    )
            case _:
                pass

    def _check_player(self, field: str, player_id: str, usable: set[str]) -> None:
        if player_id not in usable:
            self._add("dilemmas", field, f"player {player_id!r} is not in the own squad")

    def _check_squad_ref(self, field: str, slug: str) -> bool:
        if not self._known.exists(slug):
            self._add("dilemmas", field, f"unknown club-season {slug!r}")
        elif not self._known.has_squad(slug):
            self._add("dilemmas", field, f"{slug!r} has no squad (aggregate rival)")
        elif slug == self._own:
            self._add("dilemmas", field, "cannot be the own team")
        else:
            return True
        return False

    def _check_sign(self, field: str, effect: SignPlayerEffect) -> None:
        source = effect.from_club_season
        if source is not None:
            if not self._check_squad_ref(f"{field}.from_club_season", source):
                return
            squad = self._tree.squads.get(source)
            if squad is not None and effect.player_id not in {p.player_id for p in squad.players}:
                self._add(
                    "dilemmas",
                    f"{field}.from_club_season",
                    f"player {effect.player_id!r} is not in the squad of {source}",
                )
            return
        everyone = {p.player_id for s in self._tree.squads.values() for p in s.players}
        if effect.player_id not in everyone:
            self._add("dilemmas", f"{field}.player_id", f"unknown player {effect.player_id!r}")

    def _check_injury_date(self, field: str, day: date) -> None:
        first, last = self._blocks[0].start, self._blocks[-1].end
        if not first <= day <= last:
            self._add(
                "dilemmas", f"{field}.date", f"{day} is outside the season blocks ({first}..{last})"
            )


def check_playable_rationales(tree: ContentTree, sink: IssueSink) -> None:
    """The playable club-season is rated in detail: a rationale for every player."""
    for content in tree.seasons.values():
        squad = tree.squads.get(content.season.club_season)
        if squad is None:
            continue
        for index, player in enumerate(squad.players):
            if not player.rating_rationale:
                sink.add(
                    squad_path(squad.club_season),
                    f"players.{index}.rating_rationale",
                    "required for every player of a playable club-season",
                )
