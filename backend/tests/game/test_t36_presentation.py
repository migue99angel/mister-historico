"""Public Game presentation never exposes private domain or catalog data."""

from collections.abc import Sequence
from dataclasses import replace
from datetime import timedelta
from typing import cast

from tests.contracts.suites.expected_test_fc import build_expected_test_fc_season
from tests.game.test_t35_use_cases import _setup

from mister.catalog.application.api import (
    PlayableSeasonDTO,
    PlayableSeasonSummaryDTO,
    present_person_name,
)
from mister.game.infrastructure.presentation_adapter import CatalogPresentationAdapter
from mister.game.domain.squad_registry import SquadRegistry
from mister.settings import Settings
from mister.shared_kernel.ids import PlayableSeasonId


def test_published_name_helper_uses_alias_when_real_names_are_disabled() -> None:
    assert present_person_name("Real Person", "Alias Person", real_names=False) == "Alias Person"


class _Catalog:
    def __init__(self, season: PlayableSeasonDTO) -> None:
        self.season = season

    def list_playable_seasons(self) -> Sequence[PlayableSeasonSummaryDTO]:
        return (self.season.summary(),)

    def get_playable_season(self, season_id: PlayableSeasonId) -> PlayableSeasonDTO:
        assert self.season.id == season_id
        return self.season


def test_season_detail_uses_aliases_when_real_names_are_disabled() -> None:
    season = build_expected_test_fc_season()
    own_squad = season.own_club_season.squad
    assert own_squad is not None
    adapter = CatalogPresentationAdapter(_Catalog(season), Settings(real_names=False))

    result = adapter.get_season(season.id).to_json()

    assert result["historicalManager"] == season.manager.alias_name
    squad = cast("dict[str, object]", result["squad"])
    key_players = cast("list[dict[str, object]]", squad["keyPlayers"])
    assert key_players[0]["displayName"] == next(item for item in own_squad if item.key).alias_name


def test_run_presentation_uses_the_run_capture_after_catalog_changes() -> None:
    season = build_expected_test_fc_season()
    provider = _Catalog(season)
    adapter = CatalogPresentationAdapter(provider, Settings())
    original, _, store, _, start, _, _ = _setup()
    created = start.execute(original.id)
    captured = store.runs[created.run_id].replay_inputs.content
    original_squad = original.own_club_season.squad
    assert original_squad is not None
    original_player = original_squad[0]
    changed_clubs = tuple(
        replace(
            club,
            squad=tuple(replace(item, display_name="Changed Name") for item in (club.squad or ())),
        )
        if club.id == season.club_season_id
        else club
        for club in season.club_seasons
    )
    provider.season = replace(season, club_seasons=changed_clubs)

    result = adapter.present_run(created.view, captured).to_json()

    squad = cast("dict[str, object]", result["squad"])
    players = cast("list[dict[str, object]]", squad["players"])
    assert players[0]["displayName"] == original_player.display_name
    assert "seed" not in result
    dilemmas = cast("list[dict[str, object]]", result["pendingDilemmas"])
    assert all("effects" not in item for item in dilemmas)


def test_active_squad_uses_block_start_membership_date() -> None:
    season, _, store, _, start, _, _ = _setup()
    created = start.execute(season.id)
    record = store.runs[created.run_id]
    block_start = season.blocks[0].start
    player = next(
        item
        for item in season.own_club_season.squad or ()
        if created.view.run.run_state.squad_registry.owner_on(item.player_id, block_start)
        == season.club_season_id
    )
    memberships = tuple(
        replace(item, joined_on=block_start + timedelta(days=1))
        if item.player_id == player.player_id
        else item
        for item in created.view.run.run_state.squad_registry.base_memberships
    )
    state = replace(
        created.view.run.run_state,
        squad_registry=SquadRegistry(
            memberships, created.view.run.run_state.squad_registry.transfers
        ),
    )
    run = replace(created.view.run, run_state=state)
    view = replace(created.view, run=run)
    result = (
        CatalogPresentationAdapter(_Catalog(season), Settings())
        .present_run(view, record.replay_inputs.content)
        .to_json()
    )
    squad = cast("dict[str, object]", result["squad"])
    players = cast("list[dict[str, object]]", squad["players"])

    assert player.player_id.value not in {item["id"] for item in players}
