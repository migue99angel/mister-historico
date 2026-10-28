"""ACL that builds public Game presentation from published Catalog snapshots."""

from datetime import date

from mister.catalog.application import api as catalog
from mister.catalog.application.api import (
    PlayableSeasonDTO,
    SeasonContentProvider,
    TextKind,
    present_person_name,
)
from mister.game.application import ports
from mister.game.application.block_codec import BlockSimulationCodec
from mister.game.application.presentation import GamePresentation
from mister.game.application.presentation_types import Presented
from mister.game.application.run_content import RunContentSnapshot
from mister.game.application.use_cases import RunView
from mister.game.domain.run import RunStatus
from mister.game.domain.state import PlayerState
from mister.game.infrastructure.catalog_adapter import CatalogRunContentAdapter
from mister.settings import Settings
from mister.shared_kernel.ids import ClubSeasonId, CompetitionId, PlayableSeasonId, PlayerId


class CatalogPresentationAdapter(GamePresentation):
    """Translate Catalog DTOs and private Game state into safe presentation values."""

    def __init__(self, provider: SeasonContentProvider, settings: Settings) -> None:
        self._provider = provider
        self._real_names = settings.real_names

    def list_seasons(self) -> tuple[Presented, ...]:
        return tuple(
            self._season_summary(item.id) for item in self._provider.list_playable_seasons()
        )

    def get_season(self, season_id: PlayableSeasonId) -> Presented:
        season = self._provider.get_playable_season(season_id)
        own = season.own_club_season
        players = own.squad or ()
        key_players = tuple(player for player in players if player.key)
        average = sum(player.rating for player in players) / len(players) if players else 1
        presentation = next(
            (item.body for item in season.texts if item.kind is TextKind.PRESENTATION), ""
        )
        return Presented(
            {
                **self._summary_dict(season),
                "presentation": presentation,
                "boardObjectives": [
                    {
                        "id": item.id,
                        "description": item.text,
                        "competitionId": item.competition_id.value,
                    }
                    for item in season.board_objectives
                ],
                "squad": {
                    "size": len(players),
                    "averageRating": average,
                    "keyPlayers": [self._initial_player(player) for player in key_players],
                },
                "competitions": [
                    {
                        "id": item.id.value,
                        "name": item.name,
                        "kind": item.kind.value,
                        "tier": item.tier.value,
                    }
                    for item in season.competitions
                ],
                "blockCount": len(season.blocks),
            }
        )

    def present_run(self, view: RunView, content: RunContentSnapshot) -> Presented:
        season = CatalogRunContentAdapter.restore(content)
        if season.id != view.run.season_id:
            raise ValueError("run content season does not match run view")
        return Presented(self._run_view(view, season))

    def _season_summary(self, season_id: PlayableSeasonId) -> Presented:
        return Presented(self._summary_dict(self._provider.get_playable_season(season_id)))

    def _summary_dict(self, season: PlayableSeasonDTO) -> dict[str, object]:
        own = season.own_club_season
        return {
            "id": season.id.value,
            "clubName": own.name,
            "shortName": own.short_name,
            "seasonLabel": season.season,
            "historicalManager": present_person_name(
                season.manager.display_name, season.manager.alias_name, real_names=self._real_names
            ),
            "colors": {"primary": own.primary_color, "secondary": own.secondary_color},
        }

    def _initial_player(self, player: catalog.PlayerDTO) -> dict[str, object]:
        return {
            "id": player.player_id.value,
            "displayName": present_person_name(
                player.display_name, player.alias_name, real_names=self._real_names
            ),
            "position": player.position.value,
            "age": player.age,
            "rating": player.rating,
            "key": player.key,
        }

    def _run_view(self, view: RunView, season: PlayableSeasonDTO) -> dict[str, object]:
        run = view.run
        terminal = run.status is not RunStatus.IN_PROGRESS
        block_number = len(run.block_records) if terminal else run.block_index + 1
        block = run.blocks[block_number - 1]
        block_info = next(item for item in season.blocks if item.id == block.id)
        state_date = run.run_state.state_as_of or block_info.start
        squad_date = (run.cursor or state_date) if terminal else block_info.start
        catalog_players = {
            p.player_id: p for club in season.club_seasons for p in (club.squad or ())
        }
        catalog_players.update({p.player_id: p for p in season.market_players})
        current = sorted(
            (
                p
                for p in run.run_state.players
                if run.run_state.squad_registry.owner_on(p.player_id, squad_date)
                == run.run_state.managed_club_season_id
            ),
            key=lambda p: p.player_id.value,
        )
        all_results = [BlockSimulationCodec.decode(item.payload) for item in run.block_records]
        latest = all_results[-1] if all_results else None
        clubs = {item.id: item for item in season.club_seasons}
        competitions = {item.id: item for item in season.competitions}
        decided = {item.dilemma_id for item in run.decisions}
        pending = []
        for item in season.dilemmas:
            if item.block_id == block.id and item.id not in decided:
                pending.append(
                    {
                        "id": item.id.value,
                        "title": item.title,
                        "prompt": item.prompt,
                        "options": [{"id": op.id.value, "label": op.label} for op in item.options],
                    }
                )
        players = [
            self._run_player(player, catalog_players[player.player_id], state_date)
            for player in current
        ]
        average_fitness = (
            round(sum(item.fitness for item in current) / len(current)) if current else 1
        )
        return {
            "runId": str(run.id.value),
            "seasonId": run.season_id.value,
            "status": run.status.value,
            "version": view.version,
            "block": {"number": block_number, "total": len(run.blocks), "label": block_info.label},
            "pendingDilemmas": pending,
            "decisions": [
                {
                    "dilemmaId": item.dilemma_id.value,
                    "optionId": item.option_id.value,
                    "blockNumber": next(
                        i + 1 for i, b in enumerate(run.blocks) if b.id == item.block_id
                    ),
                }
                for item in run.decisions
            ],
            "state": {
                "morale": run.run_state.team_morale,
                "boardConfidence": run.run_state.board_confidence,
                "fitness": average_fitness,
            },
            "squad": {
                "size": len(players),
                "averageRating": sum(p.rating for p in current) / len(current) if current else 1,
                "players": players,
            },
            "tactic": {
                "style": run.run_state.tactic.style.value,
                "system": "-".join(map(str, run.run_state.tactic.system)),
            },
            "competitionPriorities": [
                {"competitionId": item.competition_id.value, "priority": item.priority.value}
                for item in run.run_state.competition_priorities
            ],
            "lastBlockSummary": self._block_summary(
                latest,
                all_results[-2] if len(all_results) > 1 else None,
                len(run.block_records),
                season,
                clubs,
                competitions,
                catalog_players,
            )
            if latest
            else None,
            "sackedMonth": run.cursor.month
            if run.status is RunStatus.SACKED and run.cursor
            else None,
        }

    def _run_player(
        self, player: PlayerState, source: catalog.PlayerDTO, cursor: date
    ) -> dict[str, object]:
        days = (player.injured_until - cursor).days if player.injured_until else 0
        return {
            "id": player.player_id.value,
            "displayName": present_person_name(
                source.display_name, source.alias_name, real_names=self._real_names
            ),
            "position": player.position.value,
            "age": player.age if player.age is not None else source.age,
            "rating": player.rating,
            "key": source.key,
            "morale": player.morale,
            "fitness": player.fitness,
            "injury": {"daysOut": days} if days > 0 else None,
        }

    def _block_summary(  # noqa: PLR0913, PLR0917 - all reference metadata is explicit
        self,
        result: ports.BlockSimulationResult,
        previous: ports.BlockSimulationResult | None,
        block_number: int,
        season: PlayableSeasonDTO,
        clubs: dict[ClubSeasonId, catalog.ClubSeasonDTO],
        competitions: dict[CompetitionId, catalog.CompetitionDTO],
        players: dict[PlayerId, catalog.PlayerDTO],
    ) -> dict[str, object]:
        def team(club_id: ClubSeasonId) -> dict[str, object]:
            club = clubs[club_id]
            return {
                "clubSeasonId": club.id.value,
                "name": club.name,
                "shortName": club.short_name,
                "colors": {"primary": club.primary_color, "secondary": club.secondary_color},
                "isUser": club.id == season.club_season_id,
            }

        matches = []
        for item in result.matches:
            competition = competitions[item.competition_id]
            round_label = (
                f"Jornada {item.round}"
                if item.round is not None
                else next(
                    (stage.name for stage in competition.stages if stage.id == item.stage_id),
                    None,
                )
            )
            matches.append(
                {
                    "fixtureId": item.fixture_id.value,
                    "competitionId": item.competition_id.value,
                    "competitionName": competition.name,
                    **({"round": round_label} if round_label else {}),
                    "date": item.date.isoformat(),
                    "home": team(item.home),
                    "away": team(item.away),
                    "homeGoals": item.regulation.home,
                    "awayGoals": item.regulation.away,
                    "extraTime": (
                        {"home": item.extra_time.home, "away": item.extra_time.away}
                        if item.extra_time
                        else None
                    ),
                    "penalties": (
                        {"home": item.penalties.home, "away": item.penalties.away}
                        if item.penalties
                        else None
                    ),
                    "venue": item.venue.value,
                    "isKeyMatch": item.key,
                    "keyMatchLabel": "Partido clave" if item.key else None,
                    "userResult": item.user_result.value,
                }
            )
        prior_tables = (
            {
                (item.competition_id, item.stage_id, item.group_id): item
                for item in previous.standings
            }
            if previous
            else {}
        )
        standings = []
        for table in result.standings:
            prior = prior_tables.get((table.competition_id, table.stage_id, table.group_id))
            positions = {row.club_season_id: row.position for row in prior.rows} if prior else {}
            standings.append(
                {
                    "competitionId": table.competition_id.value,
                    "competitionName": competitions[table.competition_id].name,
                    **({"stageId": table.stage_id} if table.stage_id else {}),
                    **({"groupId": table.group_id} if table.group_id else {}),
                    "rows": [
                        {
                            "position": row.position,
                            "previousPosition": positions.get(row.club_season_id),
                            "team": team(row.club_season_id),
                            "played": row.played,
                            "won": row.won,
                            "drawn": row.drawn,
                            "lost": row.lost,
                            "goalsFor": row.goals_for,
                            "goalsAgainst": row.goals_against,
                            "points": row.points,
                        }
                        for row in table.rows
                    ],
                }
            )
        events = []
        for event in result.events:
            club_name = clubs[event.club_season_id].name
            competition_name = competitions[event.competition_id].name
            if event.kind.value == "advanced":
                text = f"{club_name} avanza en {competition_name}."
            elif event.kind.value == "eliminated":
                text = f"{club_name} queda eliminado de {competition_name}."
            else:
                text = f"{club_name} gana {competition_name}."
            events.append({"kind": "milestone", "date": event.date.isoformat(), "text": text})
        injuries = [
            {
                "playerId": item.player_id.value,
                "playerName": present_person_name(
                    players[item.player_id].display_name,
                    players[item.player_id].alias_name,
                    real_names=self._real_names,
                ),
                "date": item.date.isoformat(),
                "daysOut": item.days,
            }
            for item in result.injuries
        ]
        block = next(item for item in season.blocks if item.id == result.block_id)
        return {
            "blockNumber": block_number,
            "label": block.label,
            "results": matches,
            "standings": standings,
            "events": events,
            "injuries": injuries,
        }
