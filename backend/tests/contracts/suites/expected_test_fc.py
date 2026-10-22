"""The expected `PlayableSeasonDTO` of the synthetic Test FC 2000-01 content.

This is the oracle of `SeasonContentProviderContract`: the content under
`backend/tests/fixtures/content/` is the single source of truth, and this module states what
every `SeasonContentProvider` (in memory, YAML or SQL) must publish for it. It maps the
validated content tree to DTOs in the most literal way, so each rule below is part of the
contract the adapters of T2.20 and T2.21 implement:

- `club_seasons`: every participant of any competition (the own club-season included), sorted by
  id. A squad file gives `squad`; an aggregate file gives `aggregate` and the default tactic.
  Name, short name and colours come from the club file.
- `market_players`: the squad of `_market-<season>`, if there is one.
- `goal_baseline`: always concrete (a `from_league` reference is resolved to that league's
  stats); for a league it equals its `league_stats`.
- `texts`: only the reviewed ones. Every other list keeps the order of the content files.
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
    GroupStageDTO,
    HistoricalOutcomeDTO,
    InjuryEffectDTO,
    InjuryForcedEventDTO,
    LeagueRulesDTO,
    ManagerDTO,
    MoraleEffectDTO,
    ObjectiveKind,
    PlayableSeasonDTO,
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

CONTENT_ROOT = Path(__file__).resolve().parents[2] / "fixtures" / "content"
TEST_FC_SEASON = PlayableSeasonId("test-fc-2000-01")


def load_test_fc_tree() -> ContentTree:
    """The validated Test FC content tree (what an adapter loads before serving it)."""
    return load_content_tree(CONTENT_ROOT, release=False)


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
    raise AssertionError(f"unmapped effect {effect!r}")  # pragma: no cover


def _player(entry: PlayerEntry) -> PlayerDTO:
    assert entry.age is not None
    assert entry.rating is not None
    return PlayerDTO(
        player_id=PlayerId(entry.player_id),
        display_name=entry.display_name,
        alias_name=entry.alias_name,
        position=Position(entry.position.value),
        age=entry.age,
        rating=entry.rating,
        key=entry.key,
        subrole=None if entry.subrole is None else Subrole(entry.subrole.value),
        joined_on=entry.joined_on,
        left_on=entry.left_on,
    )


def _stats(stats: sn.GoalStats) -> GoalStatsDTO:
    assert stats.matches is not None
    assert stats.home_goals is not None
    assert stats.away_goals is not None
    return GoalStatsDTO(stats.matches, stats.home_goals, stats.away_goals)


def _tiebreakers(values: tuple[sn.Tiebreaker, ...]) -> tuple[Tiebreaker, ...]:
    return tuple(Tiebreaker(value.value) for value in values)


def _stage(stage: sn.Stage) -> StageDTO:
    group_stage = None
    if stage.is_group_stage:
        assert stage.groups is not None
        assert stage.points_per_win is not None
        assert stage.points_per_draw is not None
        assert stage.tiebreakers is not None
        assert stage.advance_per_group is not None
        group_stage = GroupStageDTO(
            groups=tuple(
                GroupDTO(g.id, tuple(ClubSeasonId(p) for p in g.participants)) for g in stage.groups
            ),
            points_per_win=stage.points_per_win,
            points_per_draw=stage.points_per_draw,
            tiebreakers=_tiebreakers(stage.tiebreakers),
            advance_per_group=stage.advance_per_group,
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
    )


def _competition(competition: sn.Competition, leagues: dict[str, sn.LeagueCompetition]) -> CompetitionDTO:
    common = {
        "id": CompetitionId(competition.id),
        "name": competition.name,
        "kind": CompetitionKind(competition.kind),
        "tier": CompetitionTier(competition.tier),
        "participants": tuple(ClubSeasonId(p) for p in competition.participants),
    }
    if isinstance(competition, sn.LeagueCompetition):
        stats = _stats(competition.league_stats)
        rules = LeagueRulesDTO(
            rounds=competition.rounds,
            points_per_win=competition.points_per_win,
            points_per_draw=competition.points_per_draw,
            tiebreakers=_tiebreakers(competition.tiebreakers),
            league_stats=stats,
        )
        return CompetitionDTO(goal_baseline=stats, league=rules, **common)  # type: ignore[arg-type]
    baseline = competition.goal_baseline
    stats = (
        _stats(leagues[baseline.from_league].league_stats)
        if isinstance(baseline, sn.GoalBaselineFromLeague)
        else _stats(baseline)
    )
    stages = tuple(_stage(stage) for stage in competition.stages)
    return CompetitionDTO(goal_baseline=stats, stages=stages, **common)  # type: ignore[arg-type]


def build_expected_test_fc_season(tree: ContentTree | None = None) -> PlayableSeasonDTO:
    """What every provider must serve for `test-fc-2000-01`."""
    tree = tree or load_test_fc_tree()
    content = tree.seasons[TEST_FC_SEASON.value]
    season = content.season
    leagues = {c.id: c for c in season.competitions if isinstance(c, sn.LeagueCompetition)}

    participants = sorted({p for c in season.competitions for p in c.participants})
    club_seasons = []
    for slug in participants:
        squad = tree.squads.get(slug)
        aggregate = tree.aggregates.get(slug)
        club_season = squad or aggregate
        assert club_season is not None
        assert club_season.club is not None
        club = tree.clubs[club_season.club]
        real_league = None
        if squad is not None and squad.real_league is not None:
            league = squad.real_league
            assert league.played is not None
            assert league.goals_for is not None
            assert league.goals_against is not None
            real_league = RealLeagueDTO(
                league.competition_label, league.played, league.goals_for, league.goals_against
            )
        if squad is not None:
            tactic = _tactic(squad.default_tactic)
        else:
            tactic = TacticDTO(TacticStyle.BALANCED, "4-4-2")
        assert aggregate is None or (aggregate.attack and aggregate.defense)
        club_seasons.append(
            ClubSeasonDTO(
                id=ClubSeasonId(slug),
                club_id=ClubId(club_season.club),
                name=club.name,
                short_name=club.short_name,
                primary_color=club.colors.primary,
                secondary_color=club.colors.secondary,
                season=club_season.season,
                default_tactic=tactic,
                squad=None if squad is None else tuple(_player(p) for p in squad.players),
                aggregate=None
                if aggregate is None
                else AggregateStrengthDTO(aggregate.attack or 0, aggregate.defense or 0),
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
                    DilemmaOptionDTO(
                        OptionId(o.id), o.label, tuple(_effect(e) for e in o.effects)
                    )
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
