"""Catalog-to-Game ACL for capturing and restoring a run's immutable content."""

from datetime import date
from typing import assert_never

from mister.catalog.application import api as c
from mister.catalog.application.api import PlayableSeasonDTO, SeasonContentProvider
from mister.game.application.content_model import (
    CapturedBlock,
    CapturedDilemma,
    CapturedOption,
    CapturedRealResult,
    CapturedSeason,
    CompetitionMetadata,
    FixtureMetadata,
    HistoricalOutcomeMetadata,
    StageMetadata,
    StandingCutoffMetadata,
    StandingRowMetadata,
)
from mister.game.application.rules import RulesConfiguration
from mister.game.application.run_content import RunContentSnapshot
from mister.game.domain import effects as e
from mister.game.domain.board import GoalDefinition, GoalKind
from mister.game.domain.squad_registry import Membership, SquadRegistry
from mister.game.domain.state import (
    CompetitionPriority,
    ForcedInjury,
    PlayerState,
    Position,
    Priority,
    RunState,
    Tactic,
    TacticStyle,
)
from mister.game.infrastructure.run_content_codec import (
    decode_playable_season,
    encode_playable_season,
)
from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import ClubSeasonId, PlayableSeasonId, PlayerId


class CatalogRunContentAdapter:
    """Capture one published season exactly once and restore without consulting Catalog."""

    def __init__(self, provider: SeasonContentProvider) -> None:
        self._provider = provider

    def capture(self, season_id: PlayableSeasonId) -> RunContentSnapshot:
        season = self._provider.get_playable_season(season_id)
        if season.id != season_id:
            raise InvalidValueError("Catalog returned a different playable season identity")
        return encode_playable_season(season)

    def capture_game(
        self, season_id: PlayableSeasonId, rules: RulesConfiguration
    ) -> CapturedSeason:
        """Read Catalog once and immediately translate the captured snapshot to Game types."""
        snapshot = self.capture(season_id)
        return self.restore_game(snapshot, rules)

    @staticmethod
    def restore(snapshot: RunContentSnapshot) -> PlayableSeasonDTO:
        """Compatibility adapter for callers that need Catalog's published DTO."""
        return decode_playable_season(snapshot)

    @staticmethod
    def restore_game(snapshot: RunContentSnapshot, rules: RulesConfiguration) -> CapturedSeason:
        """Rebuild Game-owned startup and orchestration data from the private snapshot only."""
        if not isinstance(rules, RulesConfiguration):
            raise InvalidValueError("restore_game requires explicit rules")
        season = decode_playable_season(snapshot)
        start = season.blocks[0].start
        if rules.initial_state.decision_date_policy != "block_start":
            raise InvalidValueError("unsupported decision date policy")
        memberships: list[Membership] = []
        players: dict[PlayerId, PlayerState] = {}
        for club in season.club_seasons:
            if club.squad is None:
                continue
            for item in club.squad:
                memberships.append(
                    Membership(item.player_id, club.id, item.joined_on, item.left_on)
                )
                _add_player(
                    players,
                    item,
                    rules,
                )
        for item in season.market_players:
            _add_player(players, item, rules)
        initial_tactic = Tactic(
            TacticStyle(season.initial_tactic.style.value),
            tuple(int(v) for v in season.initial_tactic.system.split("-")),
        )
        forced: tuple[ForcedInjury, ...] = ()
        initial = RunState(
            season.club_season_id,
            SquadRegistry(tuple(memberships)),
            tuple(players[key] for key in sorted(players, key=lambda value: value.value)),
            initial_tactic,
            tuple(
                CompetitionPriority(item.id, Priority(rules.initial_state.initial_priority))
                for item in season.competitions
            ),
            rules.initial_state.team_morale,
            rules.initial_state.board_confidence,
            start,
            forced,
        )
        block_starts = {block.id: block.start for block in season.blocks}
        dilemmata = tuple(
            CapturedDilemma(
                item.id,
                item.block_id,
                item.historical_option,
                tuple(
                    CapturedOption(
                        option.id,
                        tuple(
                            _effect(
                                effect,
                                block_starts[item.block_id],
                                {club.id for club in season.club_seasons},
                            )
                            for effect in option.effects
                        ),
                    )
                    for option in item.options
                ),
            )
            for item in season.dilemmas
        )
        blocks = tuple(
            CapturedBlock(
                item.id, item.start, item.end, tuple(d for d in dilemmata if d.block_id == item.id)
            )
            for item in season.blocks
        )
        goals = tuple(
            GoalDefinition(
                item.id,
                item.competition_id.value,
                GoalKind(item.kind.value),
                item.target_position
                if item.kind is c.ObjectiveKind.FINISH_TOP
                else item.target_stage
                if item.kind is c.ObjectiveKind.REACH_STAGE
                else None,
            )
            for item in season.board_objectives
        )
        competitions = tuple(
            CompetitionMetadata(
                item.id,
                item.kind.value,
                item.tier.value,
                item.participants,
                tuple(
                    StageMetadata(
                        stage.id,
                        stage.round.value,
                        stage.legs,
                        stage.away_goals_rule,
                        stage.extra_time,
                        stage.penalties,
                        tuple(
                            (group.id, group.participants)
                            for group in (stage.group_stage.groups if stage.group_stage else ())
                        ),
                        stage.group_stage.advance_per_group if stage.group_stage else None,
                    )
                    for stage in item.stages
                ),
            )
            for item in season.competitions
        )
        fixtures = tuple(
            FixtureMetadata(
                item.id.value,
                item.date,
                item.competition_id,
                item.opponent,
                item.venue.value,
                item.round,
                item.stage,
                item.group,
                item.leg,
                item.key,
                CapturedRealResult(
                    item.result.goals_for,
                    item.result.goals_against,
                    item.result.extra_time,
                    item.result.penalties_for,
                    item.result.penalties_against,
                )
                if item.result
                else None,
            )
            for item in season.fixtures
        )
        outcomes = tuple(
            HistoricalOutcomeMetadata(
                item.competition_id, item.champion, item.final_position, item.eliminated_in
            )
            for item in season.historical_outcomes
        )
        standings = tuple(
            StandingCutoffMetadata(
                item.competition_id,
                item.date,
                item.stage,
                item.group,
                tuple(
                    StandingRowMetadata(
                        row.club_season_id,
                        row.position,
                        row.played,
                        row.won,
                        row.drawn,
                        row.lost,
                        row.goals_for,
                        row.goals_against,
                        row.points,
                    )
                    for row in item.table
                ),
            )
            for item in season.standings
        )
        return CapturedSeason(
            snapshot,
            season.id,
            season.club_season_id,
            season.season,
            initial,
            blocks,
            competitions,
            goals,
            fixtures,
            outcomes,
            standings,
        )


def _add_player(
    players: dict[PlayerId, PlayerState], item: c.PlayerDTO, rules: RulesConfiguration
) -> None:
    players.setdefault(
        item.player_id,
        PlayerState(
            item.player_id,
            Position(item.position.value),
            item.rating,
            item.age,
            rules.initial_state.player_morale,
            rules.initial_state.player_fitness,
        ),
    )


def _effect(  # noqa: PLR0911 - exhaustive ten-effect translation
    effect: c.EffectDTO,
    date_value: date,
    participating_clubs: set[ClubSeasonId],
) -> e.Effect:
    if isinstance(effect, c.MoraleEffectDTO):
        return e.MoraleEffect(effect.delta)
    if isinstance(effect, c.PlayerMoraleEffectDTO):
        return e.PlayerMoraleEffect(effect.player_id, effect.delta)
    if isinstance(effect, c.SignPlayerEffectDTO):
        return e.SignPlayerEffect(
            effect.player_id,
            effect.from_club_season if effect.from_club_season in participating_clubs else None,
            date_value,
        )
    if isinstance(effect, c.SellPlayerEffectDTO):
        return e.SellPlayerEffect(
            effect.player_id,
            effect.to_club_season if effect.to_club_season in participating_clubs else None,
            date_value,
        )
    if isinstance(effect, c.SetTacticEffectDTO):
        return e.SetTacticEffect(
            Tactic(TacticStyle(effect.style.value), tuple(int(v) for v in effect.system.split("-")))
        )
    if isinstance(effect, c.CompetitionPriorityEffectDTO):
        return e.CompetitionPriorityEffect(effect.competition_id, Priority(effect.priority.value))
    if isinstance(effect, c.BoardConfidenceEffectDTO):
        return e.BoardConfidenceEffect(effect.delta)
    if isinstance(effect, c.YouthMinutesEffectDTO):
        return e.YouthMinutesEffect(effect.player_id)
    if isinstance(effect, c.InjuryEffectDTO):
        return e.InjuryEffect(effect.player_id, effect.date, effect.days)
    if isinstance(effect, c.FitnessEffectDTO):
        return e.FitnessEffect(effect.delta, effect.player_id)
    assert_never(effect)
