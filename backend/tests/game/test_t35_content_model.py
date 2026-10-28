from dataclasses import replace
from typing import cast

from tests.contracts.suites.expected_test_fc import build_expected_test_fc_season

from mister.catalog.application import api as catalog
from mister.catalog.application.api import PlayableSeasonDTO, SeasonContentProvider
from mister.game.application.rules import RulesConfiguration
from mister.game.domain.effects import SellPlayerEffect, SignPlayerEffect
from mister.game.infrastructure.catalog_adapter import CatalogRunContentAdapter
from mister.game.infrastructure.run_content_codec import encode_playable_season
from mister.shared_kernel.ids import ClubSeasonId, PlayableSeasonId


def test_restore_game_rebuilds_private_state_and_market_players_without_catalog_reference() -> None:
    season = build_expected_test_fc_season()
    snapshot = encode_playable_season(season)
    captured = CatalogRunContentAdapter.restore_game(snapshot, RulesConfiguration.a_profile())
    assert captured.snapshot == snapshot
    assert captured.initial_state.managed_club_season_id == season.club_season_id
    assert captured.blocks[0].start == season.blocks[0].start
    assert captured.run_blocks[0].dilemmas
    assert captured.goals
    assert {p.player_id for p in captured.players} >= {p.player_id for p in season.market_players}
    assert all(
        captured.initial_state.squad_registry.owner_on(p.player_id, season.blocks[0].start) is None
        for p in season.market_players
    )
    assert captured.initial_state.forced_injuries == ()
    expected_memberships = {
        (player.player_id, club.id, player.joined_on, player.left_on)
        for club in season.club_seasons
        for player in club.squad or ()
    }
    observed_memberships = {
        (membership.player_id, membership.club_season_id, membership.joined_on, membership.left_on)
        for membership in captured.initial_state.squad_registry.base_memberships
    }
    assert observed_memberships == expected_memberships
    block_starts = {block.id: block.start for block in season.blocks}
    for block in captured.blocks:
        for dilemma in block.dilemmas:
            for option in dilemma.options:
                for effect in option.effects:
                    if hasattr(effect, "effective_on"):
                        assert effect.effective_on == block_starts[dilemma.block_id]
    translated = {
        type(effect).__name__
        for block in captured.blocks
        for dilemma in block.dilemmas
        for option in dilemma.options
        for effect in option.effects
    }
    assert translated == {
        "MoraleEffect",
        "PlayerMoraleEffect",
        "SignPlayerEffect",
        "SellPlayerEffect",
        "SetTacticEffect",
        "CompetitionPriorityEffect",
        "BoardConfidenceEffect",
        "YouthMinutesEffect",
        "InjuryEffect",
        "FitnessEffect",
    }


def test_capture_game_reads_provider_once_and_restores_snapshot_without_provider() -> None:
    season = build_expected_test_fc_season()

    class Provider:
        calls = 0

        def get_playable_season(self, season_id: PlayableSeasonId) -> PlayableSeasonDTO:
            self.calls += 1
            assert season_id == season.id
            return season

    provider = Provider()
    adapter = CatalogRunContentAdapter(cast("SeasonContentProvider", provider))
    captured = adapter.capture_game(
        PlayableSeasonId(season.id.value), RulesConfiguration.a_profile()
    )
    assert provider.calls == 1
    restored = CatalogRunContentAdapter.restore_game(
        captured.snapshot, RulesConfiguration.a_profile()
    )
    assert restored == captured


def test_restore_game_normalizes_external_transfer_clubs_to_market_owner() -> None:
    season = build_expected_test_fc_season()
    changed_dilemmas = []
    for dilemma in season.dilemmas:
        options = []
        for option in dilemma.options:
            effects = []
            for original_effect in option.effects:
                translated = original_effect
                if isinstance(original_effect, catalog.SignPlayerEffectDTO):
                    translated = replace(
                        original_effect,
                        from_club_season=ClubSeasonId("external-club-2000-01"),
                    )
                elif isinstance(original_effect, catalog.SellPlayerEffectDTO):
                    translated = replace(
                        original_effect,
                        to_club_season=ClubSeasonId("external-club-2000-01"),
                    )
                effects.append(translated)
            options.append(replace(option, effects=tuple(effects)))
        changed_dilemmas.append(replace(dilemma, options=tuple(options)))
    changed = replace(season, dilemmas=tuple(changed_dilemmas))
    captured = CatalogRunContentAdapter.restore_game(
        encode_playable_season(changed), RulesConfiguration.a_profile()
    )
    private_effects = tuple(
        effect
        for block in captured.blocks
        for dilemma in block.dilemmas
        for option in dilemma.options
        for effect in option.effects
    )
    assert any(
        isinstance(effect, SignPlayerEffect) and effect.from_club_season is None
        for effect in private_effects
    )
    assert any(
        isinstance(effect, SellPlayerEffect) and effect.to_club_season is None
        for effect in private_effects
    )
