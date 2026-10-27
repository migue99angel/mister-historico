"""YAML-backed published season content provider.

The validated content tree is mapped without leaking schema models to consumers.
"""

from pathlib import Path

from mister.catalog.application.api import (
    AggregateStrengthDTO,
    BlockDTO,
    BoardConfidenceEffectDTO,
    BoardObjectiveDTO,
    ClubSeasonDTO,
    CompetitionDTO,
    CompetitionKind,
    CompetitionPriorityEffectDTO,
    CompetitionTier,
    DilemmaDTO,
    DilemmaOptionDTO,
    EffectDTO,
    FitnessEffectDTO,
    FixtureDTO,
    GoalStatsDTO,
    GroupDTO,
    GroupEntryAssignmentDTO,
    GroupEntryAssignmentsDTO,
    GroupStageDTO,
    HeadToHeadEvidenceDTO,
    HeadToHeadFixtureDTO,
    HeadToHeadResultDTO,
    HistoricalOutcomeDTO,
    InjuryEffectDTO,
    InjuryForcedEventDTO,
    KnockoutCalendarDTO,
    KnockoutSlotDTO,
    LeagueRulesDTO,
    ManagerDTO,
    MoraleEffectDTO,
    ObjectiveKind,
    PlayableSeasonDTO,
    PlayableSeasonNotFoundError,
    PlayableSeasonSummaryDTO,
    PlayerDTO,
    PlayerMoraleEffectDTO,
    Position,
    Priority,
    RealLeagueDTO,
    RealResultDTO,
    RealTieDTO,
    Round,
    SellPlayerEffectDTO,
    SetTacticEffectDTO,
    SignPlayerEffectDTO,
    StageDTO,
    StandingRowDTO,
    StandingsCutoffDTO,
    Subrole,
    TacticDTO,
    TacticStyle,
    TextDTO,
    TextKind,
    Tiebreaker,
    Venue,
    YouthMinutesEffectDTO,
)
from mister.catalog.infrastructure.content_schema import ContentTree, load_content_tree
from mister.catalog.infrastructure.content_schema import effects as fx
from mister.catalog.infrastructure.content_schema import season as sn
from mister.catalog.infrastructure.content_schema.squad import PlayerEntry
from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import (
    BlockId,
    ClubId,
    ClubSeasonId,
    CompetitionId,
    DilemmaId,
    FixtureId,
    OptionId,
    PlayableSeasonId,
    PlayerId,
)


def _require[T](value: T | None, label: str) -> T:
    if value is None:
        raise InvalidValueError(f"release content needs {label}")
    return value


def _tactic(tactic: fx.Tactic) -> TacticDTO:
    return TacticDTO(TacticStyle(tactic.style), tactic.system)


def _effect(effect: object) -> EffectDTO:  # noqa: PLR0911
    match effect:
        case fx.MoraleEffect():
            return MoraleEffectDTO(effect.delta)
        case fx.PlayerMoraleEffect():
            return PlayerMoraleEffectDTO(PlayerId(effect.player_id), effect.delta)
        case fx.SignPlayerEffect():
            origin = effect.from_club_season
            return SignPlayerEffectDTO(
                PlayerId(effect.player_id), None if origin is None else ClubSeasonId(origin)
            )
        case fx.SellPlayerEffect():
            target = effect.to_club_season
            return SellPlayerEffectDTO(
                PlayerId(effect.player_id), None if target is None else ClubSeasonId(target)
            )
        case fx.SetTacticEffect():
            return SetTacticEffectDTO(TacticStyle(effect.style), effect.system)
        case fx.CompetitionPriorityEffect():
            return CompetitionPriorityEffectDTO(
                CompetitionId(effect.competition_id), Priority(effect.priority)
            )
        case fx.BoardConfidenceEffect():
            return BoardConfidenceEffectDTO(effect.delta)
        case fx.YouthMinutesEffect():
            return YouthMinutesEffectDTO(PlayerId(effect.player_id))
        case fx.InjuryEffect():
            return InjuryEffectDTO(PlayerId(effect.player_id), effect.date, effect.days)
        case fx.FitnessEffect():
            who = effect.player_id
            return FitnessEffectDTO(effect.delta, None if who is None else PlayerId(who))
    raise InvalidValueError(f"unmapped effect {effect!r}")


def _player(entry: PlayerEntry) -> PlayerDTO:
    return PlayerDTO(
        player_id=PlayerId(entry.player_id),
        display_name=entry.display_name,
        alias_name=entry.alias_name,
        position=Position(_require(entry.position, "player position").value),
        age=_require(entry.age, "player age"),
        rating=_require(entry.rating, "player rating"),
        key=entry.key,
        subrole=None if entry.subrole is None else Subrole(entry.subrole.value),
        joined_on=entry.joined_on,
        left_on=entry.left_on,
    )


def _stats(stats: sn.GoalStats) -> GoalStatsDTO:
    return GoalStatsDTO(
        _require(stats.matches, "goal baseline matches"),
        _require(stats.home_goals, "goal baseline home goals"),
        _require(stats.away_goals, "goal baseline away goals"),
    )


def _tiebreakers(values: tuple[sn.Tiebreaker, ...]) -> tuple[Tiebreaker, ...]:
    return tuple(Tiebreaker(value.value) for value in values)


def _stage(stage: sn.Stage) -> StageDTO:
    group_stage = None
    if stage.is_group_stage:
        group_stage = GroupStageDTO(
            groups=tuple(
                GroupDTO(g.id, tuple(ClubSeasonId(p) for p in g.participants))
                for g in _require(stage.groups, "groups")
            ),
            points_per_win=_require(stage.points_per_win, "group win points"),
            points_per_draw=_require(stage.points_per_draw, "group draw points"),
            tiebreakers=_tiebreakers(_require(stage.tiebreakers, "group tiebreakers")),
            advance_per_group=_require(stage.advance_per_group, "group advancing positions"),
            reapply_head_to_head=None
            if stage.reapply_head_to_head is None
            else stage.reapply_head_to_head.value,
            coefficients=tuple(
                (ClubSeasonId(value.club_season), _require(value.milli_points, "coefficient"))
                for value in stage.coefficients or ()
            ),
        )
    return StageDTO(
        stage.id,
        stage.name,
        Round(stage.round),
        stage.legs,
        stage.away_goals_rule,
        stage.extra_time,
        stage.penalties,
        group_stage,
        None if stage.away_goals_in_extra_time is None else stage.away_goals_in_extra_time.value,
    )


def _competition(
    competition: sn.Competition, leagues: dict[str, sn.LeagueCompetition]
) -> CompetitionDTO:
    competition_id = CompetitionId(competition.id)
    kind = CompetitionKind(competition.kind)
    tier = CompetitionTier(competition.tier)
    participants = tuple(ClubSeasonId(p) for p in competition.participants)
    if isinstance(competition, sn.LeagueCompetition):
        stats = _stats(competition.league_stats)
        rules = LeagueRulesDTO(
            rounds=competition.rounds,
            points_per_win=competition.points_per_win,
            points_per_draw=competition.points_per_draw,
            tiebreakers=_tiebreakers(competition.tiebreakers),
            league_stats=stats,
        )
        return CompetitionDTO(
            id=competition_id,
            name=competition.name,
            kind=kind,
            tier=tier,
            participants=participants,
            goal_baseline=stats,
            league=rules,
        )
    baseline = competition.goal_baseline
    stats = (
        _stats(leagues[baseline.from_league].league_stats)
        if isinstance(baseline, sn.GoalBaselineFromLeague)
        else _stats(baseline)
    )
    stages = tuple(_stage(stage) for stage in competition.stages)
    return CompetitionDTO(
        id=competition_id,
        name=competition.name,
        kind=kind,
        tier=tier,
        participants=participants,
        goal_baseline=stats,
        stages=stages,
    )


def _map_season(tree: ContentTree, slug: str) -> PlayableSeasonDTO:
    """Map one validated release season to the published immutable language."""
    content = tree.seasons[slug]
    season = content.season
    leagues = {c.id: c for c in season.competitions if isinstance(c, sn.LeagueCompetition)}

    participants = sorted({p for c in season.competitions for p in c.participants})
    club_seasons = []
    for club_slug in participants:
        squad = tree.squads.get(club_slug)
        aggregate = tree.aggregates.get(club_slug)
        participant = _require(squad or aggregate, "participant club-season")
        club_id = _require(participant.club, "participant club id")
        club = tree.clubs[club_id]
        real_league = None
        if squad is not None and squad.real_league is not None:
            league = squad.real_league
            real_league = RealLeagueDTO(
                league.competition_label,
                _require(league.played, "real league matches"),
                _require(league.goals_for, "real league goals for"),
                _require(league.goals_against, "real league goals against"),
            )
        if squad is not None:
            tactic = _tactic(squad.default_tactic)
        else:
            tactic = TacticDTO(TacticStyle.BALANCED, "4-4-2")
        club_seasons.append(
            ClubSeasonDTO(
                id=ClubSeasonId(club_slug),
                club_id=ClubId(club_id),
                name=club.name,
                short_name=club.short_name,
                primary_color=club.colors.primary,
                secondary_color=club.colors.secondary,
                season=participant.season,
                default_tactic=tactic,
                squad=None if squad is None else tuple(_player(p) for p in squad.players),
                aggregate=None
                if aggregate is None
                else AggregateStrengthDTO(
                    _require(aggregate.attack, "aggregate attack"),
                    _require(aggregate.defense, "aggregate defense"),
                ),
                real_league=real_league,
            )
        )

    market = tree.squads.get(f"_market-{season.season}")
    fixtures = tuple(
        FixtureDTO(
            id=FixtureId(f.id),
            date=f.date,
            competition_id=CompetitionId(f.competition),
            opponent=ClubSeasonId(f.opponent),
            venue=Venue(f.venue),
            round=f.round,
            stage=f.stage,
            leg=f.leg,
            group=f.group,
            key=f.key,
            result=None
            if f.result is None
            else RealResultDTO(
                f.result.goals_for,
                f.result.goals_against,
                f.result.extra_time,
                f.result.penalties_for,
                f.result.penalties_against,
            ),
        )
        for f in content.fixtures.fixtures
    )
    return PlayableSeasonDTO(
        id=PlayableSeasonId(season.slug),
        club_season_id=ClubSeasonId(season.club_season),
        season=season.season,
        manager=ManagerDTO(season.manager.display_name, season.manager.alias_name),
        initial_tactic=_tactic(season.initial_tactic),
        blocks=tuple(BlockDTO(BlockId(b.id), b.label, b.start, b.end) for b in season.blocks),
        competitions=tuple(_competition(c, leagues) for c in season.competitions),
        forced_events=tuple(
            InjuryForcedEventDTO(PlayerId(e.player_id), e.date, e.days)
            for e in season.forced_events
        ),
        board_objectives=tuple(
            BoardObjectiveDTO(
                o.id,
                CompetitionId(o.competition),
                ObjectiveKind(o.kind),
                o.text,
                o.target_position,
                o.target_stage,
            )
            for o in season.board_objectives
        ),
        historical_outcomes=tuple(
            HistoricalOutcomeDTO(
                CompetitionId(o.competition), o.champion, o.final_position, o.eliminated_in
            )
            for o in season.historical_outcome
        ),
        club_seasons=tuple(club_seasons),
        market_players=() if market is None else tuple(_player(p) for p in market.players),
        fixtures=fixtures,
        standings=tuple(
            StandingsCutoffDTO(
                block_id=BlockId(c.block),
                competition_id=CompetitionId(c.competition),
                date=c.date,
                table=tuple(
                    StandingRowDTO(
                        ClubSeasonId(r.club_season),
                        r.position,
                        r.played,
                        r.won,
                        r.drawn,
                        r.lost,
                        r.goals_for,
                        r.goals_against,
                        r.points,
                    )
                    for r in c.table
                ),
                stage=c.stage,
                group=c.group,
            )
            for c in content.standings.cutoffs
        ),
        head_to_head=None
        if content.standings.head_to_head is None
        else tuple(
            HeadToHeadEvidenceDTO(
                CompetitionId(h.competition),
                h.complete_through,
                tuple(ClubSeasonId(c) for c in h.covered_clubs),
                tuple(
                    HeadToHeadFixtureDTO(
                        FixtureId(f.fixture_id),
                        f.date,
                        ClubSeasonId(f.home),
                        ClubSeasonId(f.away),
                        tuple(str(url) for url in f.sources),
                        f.verify,
                        f.venue,
                    )
                    for f in h.schedule
                ),
                tuple(
                    HeadToHeadResultDTO(
                        FixtureId(r.fixture_id),
                        r.score,
                        tuple(str(url) for url in r.sources),
                        r.verify,
                    )
                    for r in h.results
                ),
                tuple(str(url) for url in h.sources),
                h.verify,
                h.stage,
                h.group,
            )
            for h in content.standings.head_to_head
        ),
        knockout_calendar=None
        if content.standings.knockout_calendar is None
        else tuple(
            KnockoutCalendarDTO(
                CompetitionId(declaration.competition),
                None
                if declaration.slots is None
                else tuple(
                    KnockoutSlotDTO(
                        FixtureId(slot.fixture_id),
                        slot.stage_id,
                        slot.date,
                        ClubSeasonId(slot.home),
                        ClubSeasonId(slot.away),
                        slot.venue,
                        slot.leg,
                        tuple(str(url) for url in slot.sources),
                        slot.verify,
                    )
                    for slot in declaration.slots
                ),
                tuple(str(url) for url in declaration.sources),
                declaration.verify,
            )
            for declaration in content.standings.knockout_calendar
        ),
        group_entry_assignments=None
        if content.standings.group_entry_assignments is None
        else tuple(
            GroupEntryAssignmentsDTO(
                CompetitionId(declaration.competition),
                None
                if declaration.entries is None
                else tuple(
                    GroupEntryAssignmentDTO(
                        entry.source_stage_id,
                        entry.group_id,
                        entry.qualifying_position,
                        entry.target_stage_id,
                        ClubSeasonId(entry.historical_representative),
                        tuple(str(url) for url in entry.sources),
                        entry.verify,
                    )
                    for entry in declaration.entries
                ),
                tuple(str(url) for url in declaration.sources),
                declaration.verify,
            )
            for declaration in content.standings.group_entry_assignments
        ),
        real_ties=tuple(
            RealTieDTO(
                CompetitionId(t.competition),
                t.stage,
                (ClubSeasonId(t.clubs[0]), ClubSeasonId(t.clubs[1])),
                None if t.winner is None else ClubSeasonId(t.winner),
                t.aggregate,
            )
            for t in content.standings.ties
        ),
        dilemmas=tuple(
            DilemmaDTO(
                id=DilemmaId(d.id),
                block_id=BlockId(d.block),
                title=d.title,
                prompt=d.prompt,
                options=tuple(
                    DilemmaOptionDTO(OptionId(o.id), o.label, tuple(_effect(e) for e in o.effects))
                    for o in d.options
                ),
                historical_option=OptionId(d.historical_option.option),
            )
            for d in content.dilemmas.dilemmas
        ),
        texts=tuple(
            TextDTO(t.id, TextKind(t.kind), t.body)
            for t in content.texts.texts
            if t.status == "reviewed"
        ),
    )


class YamlSeasonContentProvider:
    """Read validated release content from a directory of YAML files."""

    def __init__(self, root: Path) -> None:
        self._root = root
        self._seasons: dict[PlayableSeasonId, PlayableSeasonDTO] | None = None

    def _load(self) -> dict[PlayableSeasonId, PlayableSeasonDTO]:
        if self._seasons is None:
            if not self._root.is_dir():
                raise InvalidValueError(f"content root {self._root} is not a directory")
            tree = load_content_tree(self._root, release=True)
            self._seasons = {
                PlayableSeasonId(slug): _map_season(tree, slug) for slug in sorted(tree.seasons)
            }
        return self._seasons

    def list_playable_seasons(self) -> tuple[PlayableSeasonSummaryDTO, ...]:
        """Return all published season summaries ordered by id."""
        return tuple(season.summary() for season in self._load().values())

    def get_playable_season(self, season_id: PlayableSeasonId) -> PlayableSeasonDTO:
        """Return the complete season, or the published not-found error."""
        try:
            return self._load()[season_id]
        except KeyError:
            raise PlayableSeasonNotFoundError(season_id) from None
