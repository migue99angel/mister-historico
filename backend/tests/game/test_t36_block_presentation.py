"""Presentation of complete simulated reports and terminal block state."""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from typing import TYPE_CHECKING, cast

from tests.contracts.suites.expected_test_fc import build_expected_test_fc_season
from tests.game.test_t35_use_cases import _setup

from mister.catalog.application.api import (
    PlayableSeasonDTO,
    PlayableSeasonNotFoundError,
    PlayableSeasonSummaryDTO,
)
from mister.game.application import ports
from mister.game.application.block_codec import BlockSimulationCodec
from mister.game.domain.run import BlockRecord, Decision, RunStatus
from mister.game.infrastructure.presentation_adapter import CatalogPresentationAdapter
from mister.settings import Settings

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mister.game.application.use_cases import RunView
    from mister.shared_kernel.ids import PlayableSeasonId


def _json_object(value: object) -> dict[str, object]:
    return cast("dict[str, object]", value)


class _Catalog:
    def __init__(self, season: PlayableSeasonDTO) -> None:
        self.season = season

    def list_playable_seasons(self) -> Sequence[PlayableSeasonSummaryDTO]:
        return (self.season.summary(),)

    def get_playable_season(self, season_id: PlayableSeasonId) -> PlayableSeasonDTO:
        if self.season.id != season_id:
            raise PlayableSeasonNotFoundError(season_id)
        return self.season


def test_match_and_standings_report_preserves_et_penalties_and_prior_positions() -> None:
    season = build_expected_test_fc_season()
    adapter = CatalogPresentationAdapter(_Catalog(season), Settings(real_names=False))
    block = season.blocks[0]
    fixture = next(item for item in season.fixtures if item.stage == "final")
    cup = next(item for item in season.competitions if item.id == fixture.competition_id)
    group_competition = next(
        item for item in season.competitions if item.id.value == "copa-continental-test"
    )
    group_stage = next(item for item in group_competition.stages if item.group_stage is not None)
    group_data = group_stage.group_stage
    assert group_data is not None
    group = group_data.groups[0]
    participants = group.participants
    standings = tuple(
        ports.StandingRow(club_id, position, 1, 1, 0, 0, 2, 1, 3)
        for position, club_id in enumerate(participants, start=1)
    )
    previous_standings = tuple(
        ports.StandingRow(club_id, len(participants) - position + 1, 1, 0, 0, 1, 1, 2, 0)
        for position, club_id in enumerate(participants, start=1)
    )
    table = ports.Standings(group_competition.id, block.end, standings, group_stage.id, group.id)
    previous_table = ports.Standings(
        group_competition.id,
        block.start,
        previous_standings,
        group_stage.id,
        group.id,
    )
    own_id = season.club_season_id
    own_squad = season.own_club_season.squad
    assert own_squad is not None
    player = own_squad[0]
    match = ports.MatchOutcome(
        fixture.id,
        fixture.competition_id,
        fixture.date,
        own_id,
        fixture.opponent,
        ports.ScoreLine(1, 1),
        ports.TeamVenue.NEUTRAL,
        fixture.opponent,
        ports.UserResult.WIN,
        ports.ScoreLine(0, 0),
        ports.ScoreLine(5, 4),
        ports.Side.HOME,
        True,
        stage_id=fixture.stage,
    )
    result = ports.BlockSimulationResult(
        block.id,
        (match,),
        (fixture.id,),
        (table,),
        (),
        (ports.InjuryOutcome(player.player_id, fixture.date, 14),),
        (),
    )
    previous = ports.BlockSimulationResult(block.id, (), (), (previous_table,), (), (), ())

    summary = adapter._block_summary(
        result,
        previous,
        1,
        season,
        {club.id: club for club in season.club_seasons},
        {item.id: item for item in season.competitions},
        {source.player_id: source for club in season.club_seasons for source in (club.squad or ())},
    )

    reports = cast("list[dict[str, object]]", summary["results"])
    assert reports[0]["homeGoals"] == 1
    assert reports[0]["awayGoals"] == 1
    assert reports[0]["extraTime"] == {"home": 0, "away": 0}
    assert reports[0]["penalties"] == {"home": 5, "away": 4}
    assert reports[0]["venue"] == "neutral"
    assert reports[0]["round"] == next(item for item in cup.stages if item.id == fixture.stage).name
    tables = cast("list[dict[str, object]]", summary["standings"])
    assert tables[0]["stageId"] == group_stage.id
    assert tables[0]["groupId"] == group.id
    rows = cast("list[dict[str, object]]", tables[0]["rows"])
    own_row = next(
        item for item in rows if _json_object(item["team"])["clubSeasonId"] == own_id.value
    )
    assert own_row["previousPosition"] == len(participants)
    injuries = cast("list[dict[str, object]]", summary["injuries"])
    assert injuries[0]["playerName"] == player.alias_name
    assert injuries[0]["daysOut"] == 14


def test_terminal_run_presents_last_played_block_and_persisted_injury_days() -> None:
    season, _, store, _, start, _, _ = _setup()
    started = start.execute(season.id)
    record = store.runs[started.run_id]
    run = started.view.run
    first_two = season.blocks[:2]
    results = tuple(
        ports.BlockSimulationResult(block.id, (), (), (), (), (), ()) for block in first_two
    )
    closed = tuple(
        BlockRecord(block.id, BlockSimulationCodec.encode(result))
        for block, result in zip(first_two, results, strict=True)
    )
    decisions = tuple(
        Decision(block.id, dilemma.id, dilemma.options[0].id, sequence)
        for sequence, (block, dilemma) in enumerate(
            (
                (run_block, dilemma)
                for run_block in run.blocks[:2]
                for dilemma in run_block.dilemmas
            ),
            start=1,
        )
    )
    cursor = season.blocks[1].end
    player_state = next(
        item
        for item in run.run_state.players
        if run.run_state.squad_registry.owner_on(item.player_id, cursor)
        == run.run_state.managed_club_season_id
    )
    state = replace(
        run.run_state,
        state_as_of=cursor,
        players=tuple(
            replace(item, injured_until=cursor + timedelta(days=5))
            if item.player_id == player_state.player_id
            else item
            for item in run.run_state.players
        ),
    )
    terminal = replace(
        run,
        status=RunStatus.SACKED,
        run_state=state,
        block_index=1,
        decisions=decisions,
        block_records=closed,
        cursor=cursor,
    )
    view: RunView = replace(started.view, run=terminal)
    result = (
        CatalogPresentationAdapter(_Catalog(season), Settings())
        .present_run(view, record.replay_inputs.content)
        .to_json()
    )

    assert result["status"] == "sacked"
    assert result["block"] == {
        "number": 2,
        "total": len(season.blocks),
        "label": season.blocks[1].label,
    }
    assert result["pendingDilemmas"] == []
    assert result["sackedMonth"] == cursor.month
    squad = cast("dict[str, object]", result["squad"])
    players = cast("list[dict[str, object]]", squad["players"])
    injured = next(item for item in players if item["id"] == player_state.player_id.value)
    assert injured["injury"] == {"daysOut": 5}
    summary = cast("dict[str, object]", result["lastBlockSummary"])
    assert summary["blockNumber"] == 2
