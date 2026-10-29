"""Immutable key-starter boundary values; execution is wired by T3.9."""

from dataclasses import dataclass
from datetime import date
from typing import Literal

from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import BlockId, FixtureId, PlayerId

_MAX_STARTERS = 11

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
            or len(self.starter_ids) > _MAX_STARTERS
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


@dataclass(frozen=True, slots=True)
class KeyStarterOffer:
    """One durable offer per block, captured before any choice or simulation."""

    block_id: BlockId
    fixture_id: FixtureId
    date: date
    candidate_ids: tuple[PlayerId, ...]
    selected_player_id: PlayerId | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.block_id, BlockId):
            raise InvalidValueError("starter offer needs a typed block ID")
        if (
            not isinstance(self.candidate_ids, tuple)
            or not self.candidate_ids
            or any(not isinstance(player, PlayerId) for player in self.candidate_ids)
            or len(set(self.candidate_ids)) != len(self.candidate_ids)
        ):
            raise InvalidValueError("starter candidates must be distinct immutable typed IDs")
        KeyStarterSelection(self.fixture_id, self.date, self.candidate_ids[0])
        if (
            self.selected_player_id is not None
            and self.selected_player_id not in self.candidate_ids
        ):
            raise InvalidValueError("selected starter must belong to the captured candidates")
