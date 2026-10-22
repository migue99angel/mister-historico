"""Builders of fictional content DTOs (Test FC 2000-01) shared by the contract suites.

Never real data (CLAUDE.md): clubs, players and results are made up. The sample covers every
shape of the published language: a league, a cup, a continental cup with a group stage, a
forced injury, standings and ties, and one option per effect type of the closed DSL.
"""

from datetime import date

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
    TacticDTO,
    TacticStyle,
    TextDTO,
    TextKind,
    Tiebreaker,
    Venue,
    YouthMinutesEffectDTO,
)
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

LEAGUE = CompetitionId("liga-test")
CUP = CompetitionId("copa-test")
CONTINENTAL = CompetitionId("copa-continental-test")
FOUR_FOUR_TWO = TacticDTO(TacticStyle.BALANCED, "4-4-2")


def _player(slug: str, position: Position, rating: int, *, key: bool = False) -> PlayerDTO:
    return PlayerDTO(
        player_id=PlayerId(slug),
        display_name=f"Player {slug}",
        alias_name=f"Alias {slug}",
        position=position,
        age=25,
        rating=rating,
        key=key,
    )


def _club_season(
    club: str, season: str, *, squad: bool = True, name: str | None = None
) -> ClubSeasonDTO:
    return ClubSeasonDTO(
        id=ClubSeasonId(f"{club}-{season}"),
        club_id=ClubId(club),
        name=name or club.replace("-", " ").title(),
        short_name=club[:3].upper(),
        primary_color="#1F4E79",
        secondary_color="#FFFFFF",
        season=season,
        default_tactic=FOUR_FOUR_TWO,
        squad=(
            (
                _player(f"{club[:3]}-01", Position.GK, 60),
                _player(f"{club[:3]}-02", Position.DF, 62, key=True),
            )
            if squad
            else None
        ),
        aggregate=None if squad else AggregateStrengthDTO(attack=40, defense=38),
        real_league=RealLeagueDTO("Liga Test", played=10, goals_for=8, goals_against=11)
        if squad
        else None,
    )


def make_sample_season(club: str = "test-fc", season: str = "2000-01") -> PlayableSeasonDTO:
    """A small but complete playable season for `club`, with a fictional rival and a cup."""
    own = _club_season(club, season, name="Test FC")
    rival = _club_season("sample-united", season)
    minnow = _club_season("placeholder-town", season, squad=False)
    own_id, rival_id, minnow_id = own.id, rival.id, minnow.id
    stats = GoalStatsDTO(matches=2, home_goals=3, away_goals=1)
    b1, b2 = BlockId("b1"), BlockId("b2")
    final = StageDTO("final", "Final", Round.FINAL, 1, False, True, True)
    groups = StageDTO(
        "groups",
        "Group stage",
        Round.GROUP_STAGE,
        2,
        False,
        False,
        False,
        group_stage=GroupStageDTO(
            groups=(GroupDTO("a", (own_id, rival_id)),),
            points_per_win=3,
            points_per_draw=1,
            tiebreakers=(Tiebreaker.HEAD_TO_HEAD_POINTS, Tiebreaker.GOAL_DIFFERENCE),
            advance_per_group=1,
        ),
    )
    star = PlayerId(f"{club[:3]}-02")
    rival_star = PlayerId("sam-02")
    market = PlayerId("mkt-01")
    options = (
        DilemmaOptionDTO(
            OptionId("a"),
            "Sign a free agent",
            (
                SignPlayerEffectDTO(market),
                BoardConfidenceEffectDTO(3),
                MoraleEffectDTO(2),
                PlayerMoraleEffectDTO(star, -4),
            ),
        ),
        DilemmaOptionDTO(
            OptionId("b"),
            "Raid the rival",
            (
                SignPlayerEffectDTO(rival_star, from_club_season=rival_id),
                SellPlayerEffectDTO(star, to_club_season=rival_id),
                SetTacticEffectDTO(TacticStyle.COUNTER, "4-3-3"),
                CompetitionPriorityEffectDTO(CUP, Priority.HIGH),
            ),
        ),
        DilemmaOptionDTO(
            OptionId("c"),
            "Rest everyone",
            (
                YouthMinutesEffectDTO(star),
                InjuryEffectDTO(star, date(2000, 10, 20), 14),
                FitnessEffectDTO(5),
                FitnessEffectDTO(-5, star),
                SellPlayerEffectDTO(star),
            ),
        ),
        DilemmaOptionDTO(OptionId("d"), "Do nothing", ()),
    )
    return PlayableSeasonDTO(
        id=PlayableSeasonId(f"{club}-{season}"),
        club_season_id=own_id,
        season=season,
        manager=ManagerDTO("Mister Ficticio", "El Profesor"),
        initial_tactic=FOUR_FOUR_TWO,
        blocks=(
            BlockDTO(b1, "August-September", date(2000, 8, 1), date(2000, 9, 30)),
            BlockDTO(b2, "October-November", date(2000, 10, 1), date(2000, 11, 30)),
        ),
        competitions=(
            CompetitionDTO(
                id=LEAGUE,
                name="Liga Test",
                kind=CompetitionKind.LEAGUE,
                tier=CompetitionTier.DOMESTIC_LEAGUE,
                participants=(own_id, rival_id),
                goal_baseline=stats,
                league=LeagueRulesDTO(
                    rounds=2,
                    points_per_win=3,
                    points_per_draw=1,
                    tiebreakers=(Tiebreaker.GOAL_DIFFERENCE, Tiebreaker.GOALS_FOR),
                    league_stats=stats,
                ),
            ),
            CompetitionDTO(
                id=CUP,
                name="Copa Test",
                kind=CompetitionKind.CUP,
                tier=CompetitionTier.DOMESTIC_CUP,
                participants=(own_id, rival_id, minnow_id),
                goal_baseline=stats,
                stages=(final,),
            ),
            CompetitionDTO(
                id=CONTINENTAL,
                name="Copa Continental Test",
                kind=CompetitionKind.CONTINENTAL_CUP,
                tier=CompetitionTier.CONTINENTAL_PRIMARY,
                participants=(own_id, rival_id),
                goal_baseline=GoalStatsDTO(matches=12, home_goals=20, away_goals=14),
                stages=(groups, final),
            ),
        ),
        forced_events=(InjuryForcedEventDTO(star, date(2000, 11, 10), 21),),
        board_objectives=(
            BoardObjectiveDTO(
                "obj-liga", LEAGUE, ObjectiveKind.FINISH_TOP, "Finish top three.", target_position=3
            ),
            BoardObjectiveDTO(
                "obj-copa", CUP, ObjectiveKind.REACH_STAGE, "Reach the final.", target_stage="final"
            ),
            BoardObjectiveDTO("obj-cont", CONTINENTAL, ObjectiveKind.WIN, "Win it."),
        ),
        historical_outcomes=(
            HistoricalOutcomeDTO(LEAGUE, champion=False, final_position=2),
            HistoricalOutcomeDTO(CUP, champion=True),
            HistoricalOutcomeDTO(CONTINENTAL, champion=False, eliminated_in="groups"),
        ),
        club_seasons=(own, rival, minnow),
        market_players=(_player("mkt-01", Position.MF, 55),),
        fixtures=(
            FixtureDTO(
                id=FixtureId(f"{club[:3]}-liga-01"),
                date=date(2000, 9, 2),
                competition_id=LEAGUE,
                opponent=rival_id,
                venue=Venue.HOME,
                round=1,
                result=RealResultDTO(2, 1),
            ),
            FixtureDTO(
                id=FixtureId(f"{club[:3]}-copa-final"),
                date=date(2001, 5, 26),
                competition_id=CUP,
                opponent=rival_id,
                venue=Venue.NEUTRAL,
                stage="final",
                key=True,
                result=RealResultDTO(1, 1, extra_time=True, penalties_for=4, penalties_against=3),
            ),
            FixtureDTO(
                id=FixtureId(f"{club[:3]}-cont-g1"),
                date=date(2000, 9, 12),
                competition_id=CONTINENTAL,
                opponent=rival_id,
                venue=Venue.AWAY,
                stage="groups",
                group="a",
                round=1,
                leg=None,
                result=None,
            ),
        ),
        standings=(
            StandingsCutoffDTO(
                block_id=b1,
                competition_id=LEAGUE,
                date=date(2000, 9, 30),
                table=(
                    StandingRowDTO(rival_id, 1, 2, 2, 0, 0, 5, 1, 6),
                    StandingRowDTO(own_id, 2, 2, 1, 0, 1, 3, 3, 3),
                ),
            ),
            StandingsCutoffDTO(
                block_id=b2,
                competition_id=CONTINENTAL,
                date=date(2000, 11, 30),
                stage="groups",
                group="a",
                table=(
                    StandingRowDTO(own_id, 1, 1, 1, 0, 0, 1, 0, 3),
                    StandingRowDTO(rival_id, 2, 1, 0, 0, 1, 0, 1, 0),
                ),
            ),
        ),
        real_ties=(
            RealTieDTO(CUP, "final", (own_id, rival_id), winner=own_id, aggregate="1-1 (4-3 pens)"),
            RealTieDTO(CUP, "semifinal", (rival_id, minnow_id), winner=None),
        ),
        dilemmas=(
            DilemmaDTO(
                id=DilemmaId("d01"),
                block_id=b1,
                title="A midfield reinforcement",
                prompt="The board lets you strengthen the squad.",
                options=options,
                historical_option=OptionId("a"),
            ),
        ),
        texts=(TextDTO("presentation.intro", TextKind.PRESENTATION, "Welcome to Test FC."),),
    )
