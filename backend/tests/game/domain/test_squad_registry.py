from datetime import date

import pytest

from mister.game.domain.squad_registry import Membership, SquadRegistry
from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import ClubSeasonId, PlayerId


def test_base_membership_is_inclusive_on_both_dates() -> None:
    registry = SquadRegistry((Membership(PlayerId("player-a"), ClubSeasonId("club-a"), date(2000, 1, 2), date(2000, 1, 4)),))

    assert registry.owner_on(PlayerId("player-a"), date(2000, 1, 1)) is None
    assert registry.owner_on(PlayerId("player-a"), date(2000, 1, 2)) == ClubSeasonId("club-a")
    assert registry.owner_on(PlayerId("player-a"), date(2000, 1, 4)) == ClubSeasonId("club-a")
    assert registry.owner_on(PlayerId("player-a"), date(2000, 1, 5)) is None


def test_overlapping_base_memberships_are_rejected_including_same_club() -> None:
    player = PlayerId("player-a")
    club = ClubSeasonId("club-a")
    with pytest.raises(InvalidValueError):
        SquadRegistry((Membership(player, club, date(2000, 1, 1), date(2000, 1, 3)), Membership(player, club, date(2000, 1, 3), None)))


def test_membership_with_reversed_dates_is_rejected() -> None:
    with pytest.raises(InvalidValueError):
        Membership(PlayerId("player-a"), ClubSeasonId("club-a"), date(2000, 1, 2), date(2000, 1, 1))


def test_transfer_moves_membership_on_effective_date_and_preserves_history() -> None:
    player = PlayerId("player-a")
    first = ClubSeasonId("club-a")
    second = ClubSeasonId("club-b")
    registry = SquadRegistry((Membership(player, first),))

    moved = registry.transfer(player, first, second, date(2000, 1, 5))

    assert registry.owner_on(player, date(2000, 1, 6)) == first
    assert moved.owner_on(player, date(2000, 1, 4)) == first
    assert moved.owner_on(player, date(2000, 1, 5)) == second
    assert moved.owner_on(player, date(2000, 1, 6)) == second
    assert moved.squad_on(first, date(2000, 1, 4)) == (player,)
    assert moved.squad_on(first, date(2000, 1, 5)) == ()
    assert moved.squad_on(second, date(2000, 1, 5)) == (player,)


def test_transfer_rejects_incorrect_origin_and_same_club() -> None:
    player = PlayerId("player-a")
    first = ClubSeasonId("club-a")
    second = ClubSeasonId("club-b")
    registry = SquadRegistry((Membership(player, first),))
    with pytest.raises(InvalidValueError):
        registry.transfer(player, second, first, date(2000, 1, 5))
    with pytest.raises(InvalidValueError):
        registry.transfer(player, first, first, date(2000, 1, 5))


def test_market_moves_support_entry_exit_and_return() -> None:
    player = PlayerId("player-a")
    club = ClubSeasonId("club-a")
    registry = SquadRegistry((Membership(player, club),))
    at_market = registry.transfer(player, club, None, date(2000, 1, 5))
    returned = at_market.transfer(player, None, club, date(2000, 1, 8))

    assert at_market.owner_on(player, date(2000, 1, 5)) is None
    assert returned.owner_on(player, date(2000, 1, 7)) is None
    assert returned.owner_on(player, date(2000, 1, 8)) == club


def test_transfer_rejects_unknown_player_and_two_moves_on_same_day() -> None:
    player = PlayerId("player-a")
    club = ClubSeasonId("club-a")
    registry = SquadRegistry((Membership(player, club),))
    with pytest.raises(InvalidValueError):
        registry.transfer(PlayerId("player-b"), None, club, date(2000, 1, 5))
    moved = registry.transfer(player, club, None, date(2000, 1, 5))
    with pytest.raises(InvalidValueError):
        moved.transfer(player, None, club, date(2000, 1, 5))
