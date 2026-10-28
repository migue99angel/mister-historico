"""Dated squad changes cross the Game to Simulation ACL without losing dates."""

from dataclasses import replace
from datetime import date

import pytest
from tests.contracts.suites.game_samples import make_simulation_request

from mister.game.application.ports import SquadMembership
from mister.game.infrastructure.simulation_mapping import to_simulation_request
from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import ClubSeasonId, PlayerId


def test_mapping_preserves_inclusive_squad_intervals_and_original_pool() -> None:
    request = make_simulation_request()
    own = request.managed_team.club_season_id
    player = request.managed_team.players[0]
    interval = SquadMembership(player.player_id, own, date(2000, 9, 2), date(2000, 9, 3))
    request = replace(
        request,
        squad_memberships=(interval,),
        player_pool=(player,),
    )

    mapped = to_simulation_request(request)

    assert mapped.squad_memberships is not None
    assert mapped.squad_memberships[0].joined_on == date(2000, 9, 2)
    assert mapped.squad_memberships[0].left_on == date(2000, 9, 3)
    assert mapped.player_pool is not None
    assert mapped.player_pool[0].player_id == player.player_id


def test_legacy_request_keeps_both_dated_fields_absent() -> None:
    mapped = to_simulation_request(make_simulation_request())

    assert mapped.squad_memberships is None
    assert mapped.player_pool is None


def test_request_rejects_partial_dated_inputs() -> None:
    with pytest.raises(InvalidValueError):
        replace(make_simulation_request(), squad_memberships=())


def test_request_rejects_duplicate_player_pool_entries() -> None:
    request = make_simulation_request()
    player = request.managed_team.players[0]

    with pytest.raises(InvalidValueError):
        replace(request, squad_memberships=(), player_pool=(player, player))


def test_request_rejects_membership_player_outside_pool() -> None:
    request = make_simulation_request()
    player = request.managed_team.players[0]
    membership = SquadMembership(PlayerId("other-player"), ClubSeasonId("test-fc-2000-01"))

    with pytest.raises(InvalidValueError):
        replace(request, squad_memberships=(membership,), player_pool=(player,))
