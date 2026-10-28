"""Private dated roster intervals used by the pure season coordinator."""

from dataclasses import dataclass
from datetime import date

from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import ClubSeasonId, PlayerId


@dataclass(frozen=True, slots=True)
class DatedMembership:
    player_id: PlayerId
    club_season_id: ClubSeasonId
    joined_on: date | None
    left_on: date | None

    def active_on(self, on: date) -> bool:
        return (self.joined_on is None or self.joined_on <= on) and (
            self.left_on is None or on <= self.left_on
        )


def validate_memberships(memberships: tuple[DatedMembership, ...]) -> None:
    for index, item in enumerate(memberships):
        for other in memberships[index + 1 :]:
            if item.player_id != other.player_id:
                continue
            first_start = item.joined_on or date.min
            first_end = item.left_on or date.max
            second_start = other.joined_on or date.min
            second_end = other.left_on or date.max
            if first_start <= second_end and second_start <= first_end:
                raise InvalidValueError("a player cannot have overlapping memberships")


def owner_on(
    memberships: tuple[DatedMembership, ...], player_id: PlayerId, on: date
) -> ClubSeasonId | None:
    return next(
        (
            item.club_season_id
            for item in memberships
            if item.player_id == player_id and item.active_on(on)
        ),
        None,
    )
