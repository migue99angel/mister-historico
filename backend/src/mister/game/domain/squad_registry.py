"""Immutable in-run squad ownership history (ADR-015)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import ClubSeasonId, PlayerId


def _is_date(value: object) -> bool:
    return isinstance(value, date) and not isinstance(value, datetime)


@dataclass(frozen=True, slots=True)
class Membership:
    """A base roster interval, with inclusive optional bounds."""

    player_id: PlayerId
    club_season_id: ClubSeasonId
    joined_on: date | None = None
    left_on: date | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.player_id, PlayerId) or not isinstance(
            self.club_season_id, ClubSeasonId
        ):
            raise InvalidValueError("Membership requires a player ID and club-season ID")
        if self.joined_on is not None and not _is_date(self.joined_on):
            raise InvalidValueError("joined_on must be a date or None")
        if self.left_on is not None and not _is_date(self.left_on):
            raise InvalidValueError("left_on must be a date or None")
        if (
            self.joined_on is not None
            and self.left_on is not None
            and self.joined_on > self.left_on
        ):
            raise InvalidValueError("Membership joined_on must not be after left_on")


@dataclass(frozen=True, slots=True)
class SquadTransfer:
    """A simulated transfer effective at the start of its date."""

    player_id: PlayerId
    from_club_season_id: ClubSeasonId | None
    to_club_season_id: ClubSeasonId | None
    effective_on: date

    def __post_init__(self) -> None:
        if not isinstance(self.player_id, PlayerId):
            raise InvalidValueError("SquadTransfer requires a player ID")
        if self.from_club_season_id is not None and not isinstance(
            self.from_club_season_id, ClubSeasonId
        ):
            raise InvalidValueError("Transfer origin must be a club-season ID or None")
        if self.to_club_season_id is not None and not isinstance(
            self.to_club_season_id, ClubSeasonId
        ):
            raise InvalidValueError("Transfer destination must be a club-season ID or None")
        if self.from_club_season_id is None and self.to_club_season_id is None:
            raise InvalidValueError("A transfer must have an origin or destination")
        if self.from_club_season_id == self.to_club_season_id:
            raise InvalidValueError("Transfer origin and destination must differ")
        if not _is_date(self.effective_on):
            raise InvalidValueError("effective_on must be a date")


@dataclass(frozen=True, slots=True)
class SquadRegistry:
    """Read-only base memberships plus immutable, simulated changes."""

    base_memberships: tuple[Membership, ...] = ()
    transfers: tuple[SquadTransfer, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.base_memberships, tuple) or not isinstance(self.transfers, tuple):
            raise InvalidValueError("Squad registry collections must be tuples")
        if any(not isinstance(item, Membership) for item in self.base_memberships):
            raise InvalidValueError("base_memberships must contain Membership values")
        if any(not isinstance(item, SquadTransfer) for item in self.transfers):
            raise InvalidValueError("transfers must contain SquadTransfer values")
        for index, membership in enumerate(self.base_memberships):
            for other in self.base_memberships[index + 1 :]:
                if membership.player_id == other.player_id and _overlap(membership, other):
                    raise InvalidValueError("A player cannot have overlapping base memberships")
        last_date: dict[PlayerId, date] = {}
        previous_transfers: list[SquadTransfer] = []
        for transfer in self.transfers:
            previous_date = last_date.get(transfer.player_id)
            if previous_date is not None and transfer.effective_on <= previous_date:
                raise InvalidValueError(
                    "Transfers for each player must be appended in chronological order"
                )
            actual_owner = _owner_on(
                self.base_memberships,
                tuple(previous_transfers),
                transfer.player_id,
                transfer.effective_on,
            )
            if actual_owner != transfer.from_club_season_id:
                raise InvalidValueError(
                    "Transfer origin does not own the player on its effective date"
                )
            last_date[transfer.player_id] = transfer.effective_on
            previous_transfers.append(transfer)

    @property
    def player_ids(self) -> frozenset[PlayerId]:
        """All players referenced by the base roster or transfer history."""
        return frozenset(
            [membership.player_id for membership in self.base_memberships]
            + [transfer.player_id for transfer in self.transfers]
        )

    def transfer(
        self,
        player_id: PlayerId,
        from_club_season_id: ClubSeasonId | None,
        to_club_season_id: ClubSeasonId | None,
        effective_on: date,
    ) -> SquadRegistry:
        """Return a registry with one validated movement appended."""
        movement = SquadTransfer(player_id, from_club_season_id, to_club_season_id, effective_on)
        last_movement_date = max(
            (item.effective_on for item in self.transfers if item.player_id == player_id),
            default=None,
        )
        if last_movement_date is not None and effective_on <= last_movement_date:
            raise InvalidValueError(
                "Transfers for each player must be appended in chronological order"
            )
        if self.owner_on(player_id, effective_on) != from_club_season_id:
            raise InvalidValueError("Transfer origin does not own the player on its effective date")
        return SquadRegistry(self.base_memberships, (*self.transfers, movement))

    def owner_on(self, player_id: PlayerId, on: date) -> ClubSeasonId | None:
        """Return the effective club; None means outside the participating clubs/market."""
        if not isinstance(player_id, PlayerId) or not _is_date(on):
            raise InvalidValueError("owner_on requires a player ID and date")
        return _owner_on(self.base_memberships, self.transfers, player_id, on)

    def squad_on(self, club_season_id: ClubSeasonId, on: date) -> tuple[PlayerId, ...]:
        """Return the club's effective squad in stable player-ID order."""
        if not isinstance(club_season_id, ClubSeasonId) or not _is_date(on):
            raise InvalidValueError("squad_on requires a club-season ID and date")
        return tuple(
            sorted(
                [
                    player_id
                    for player_id in self.player_ids
                    if self.owner_on(player_id, on) == club_season_id
                ],
                key=lambda player_id: player_id.value,
            )
        )


def _overlap(first: Membership, second: Membership) -> bool:
    starts_before_second_ends = (
        second.left_on is None or first.joined_on is None or first.joined_on <= second.left_on
    )
    starts_before_first_ends = (
        first.left_on is None or second.joined_on is None or second.joined_on <= first.left_on
    )
    return starts_before_second_ends and starts_before_first_ends


def _contains(membership: Membership, on: date) -> bool:
    return (membership.joined_on is None or membership.joined_on <= on) and (
        membership.left_on is None or on <= membership.left_on
    )


def _owner_on(
    memberships: tuple[Membership, ...],
    transfers: tuple[SquadTransfer, ...],
    player_id: PlayerId,
    on: date,
) -> ClubSeasonId | None:
    movements = [
        item for item in transfers if item.player_id == player_id and item.effective_on <= on
    ]
    if movements:
        return max(movements, key=lambda item: item.effective_on).to_club_season_id
    for membership in memberships:
        if membership.player_id == player_id and _contains(membership, on):
            return membership.club_season_id
    return None
