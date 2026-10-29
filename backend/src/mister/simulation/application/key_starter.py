"""Immutable key-starter boundary values; execution is wired by T3.9."""

from dataclasses import dataclass
from datetime import date
from typing import Literal

from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import FixtureId, PlayerId

type StarterAbsenceReason = Literal[
    "injured", "not_in_squad", "youth_conflict", "fixture_not_played"
]


@dataclass(frozen=True, slots=True)
class KeyStarterSelection:
    """One captured choice, applicable only to this fixture on this date."""

    fixture_id: FixtureId
    date: date
    player_id: PlayerId

    def __post_init__(self) -> None:
        if (
            not isinstance(self.fixture_id, FixtureId)
            or type(self.date) is not date
            or not isinstance(self.player_id, PlayerId)
        ):
            raise InvalidValueError("starter selection needs typed IDs and an exact date")


@dataclass(frozen=True, slots=True)
class KeyStarterOutcome:
    """Actual starters, without claiming the selected player caused a match result.

    An empty lineup is valid only when the fixture was not played. A nonempty lineup
    must include the selected player exactly when there is no absence reason.
    """

    fixture_id: FixtureId
    date: date
    player_id: PlayerId
    starter_ids: tuple[PlayerId, ...]
    absence_reason: StarterAbsenceReason | None = None

    def __post_init__(self) -> None:
        KeyStarterSelection(self.fixture_id, self.date, self.player_id)
        if (
            not isinstance(self.starter_ids, tuple)
            or any(not isinstance(player, PlayerId) for player in self.starter_ids)
            or len(set(self.starter_ids)) != len(self.starter_ids)
            or len(self.starter_ids) > 11
        ):
            raise InvalidValueError("starters must be at most eleven distinct typed IDs")
        if self.absence_reason not in {
            None,
            "injured",
            "not_in_squad",
            "youth_conflict",
            "fixture_not_played",
        }:
            raise InvalidValueError("unknown starter absence reason")
        if self.absence_reason == "fixture_not_played":
            if self.starter_ids:
                raise InvalidValueError("an unplayed fixture cannot have starters")
        elif not self.starter_ids:
            raise InvalidValueError("a played fixture needs actual starters")
        elif (self.player_id in self.starter_ids) != (self.absence_reason is None):
            raise InvalidValueError("starter evidence contradicts the absence reason")
