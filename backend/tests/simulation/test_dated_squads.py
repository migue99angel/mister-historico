"""Fixture-date squad selection retains all players' physical state."""

from dataclasses import replace
from datetime import date

import pytest
from tests.simulation.unit.test_simulate_block import (
    END,
    ME,
    START,
    FixedMatches,
    play,
    request,
)

from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import ClubSeasonId, PlayerId
from mister.simulation.application.api import SquadMembershipInput
from mister.simulation.application.simulate_block import _map_request


def test_membership_bounds_are_inclusive_on_both_fixture_dates() -> None:
    value = request()
    player = value.managed_team.players[0]
    membership = SquadMembershipInput(player.player_id, ME, START, START)
    value = replace(value, squad_memberships=(membership,), player_pool=value.managed_team.players)
    spy = FixedMatches()

    summary = play(value, spy)

    assert summary.block_id == value.block_id
    assert len(spy.setups) == 2


def test_effective_transfer_date_selects_the_player_for_destination_fixture() -> None:
    value = request()
    player = value.managed_team.players[0]
    membership = SquadMembershipInput(player.player_id, ME, None, date(2000, 9, 1))
    moved = SquadMembershipInput(player.player_id, ClubSeasonId("sample-united-2000-01"), START, None)
    value = replace(value, squad_memberships=(membership, moved), player_pool=value.managed_team.players)

    _map_request(value)


def test_dated_memberships_reject_overlapping_player_clubs() -> None:
    value = request()
    player = value.managed_team.players[0]
    memberships = (
        SquadMembershipInput(player.player_id, ME, START, END),
        SquadMembershipInput(player.player_id, ClubSeasonId("sample-united-2000-01"), END, None),
    )
    with pytest.raises(InvalidValueError):
        replace(value, squad_memberships=memberships, player_pool=value.managed_team.players)

