"""Durable per-block key starter interaction: offer, selection and omission (T3.9)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from typing import Literal, cast

from mister.game.application.key_starter import KeyStarterOffer
from mister.game.application.run_codec import _decode, _encode
from mister.game.domain.state import PlayerState
from mister.shared_kernel.errors import DomainError, InvalidValueError
from mister.shared_kernel.ids import BlockId, ClubSeasonId, CompetitionId, FixtureId, PlayerId

# Same policy as the key match label of `MatchReport`.
KEY_MATCH_LABEL = "Partido clave"
MAX_CANDIDATES = 3
MIN_CANDIDATES = 2

_ENTRY_KEYS = {"block_id", "offer", "players", "selected_after", "omitted"}
_OFFER_KEYS = {
    "fixture_id",
    "date",
    "candidate_ids",
    "opponent_id",
    "competition_id",
    "venue",
    "key_match_label",
    "projected_starter_ids",
    "selected_player_id",
}


class InvalidKeyStarterError(DomainError):
    """No offer, a foreign or closed fixture, or a player outside the captured candidates."""

    code = "invalid_key_starter"


class KeyStarterAlreadySelectedError(DomainError):
    """The offer of this block already has an immutable selection."""

    code = "key_starter_already_selected"


@dataclass(frozen=True, slots=True)
class KeyStarterEntry:
    """What a block captured on entry and what happened to its offer.

    `players` is the entry state of the projected starters and candidates, in that order,
    so the offer reads the same after sales, reloads or later physical changes.
    `selected_after` is the number of logged decisions when the selection was taken, which
    preserves the original command order for replay. `omitted` closes an unselected offer.
    """

    block_id: BlockId
    offer: KeyStarterOffer | None = None
    players: tuple[PlayerState, ...] = ()
    selected_after: int | None = None
    omitted: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.block_id, BlockId):
            raise InvalidValueError("key starter entry needs a typed block ID")
        if self.offer is None:
            if self.players or self.selected_after is not None or self.omitted:
                raise InvalidValueError("a block without offer has no captured interaction")
            return
        if not isinstance(self.offer, KeyStarterOffer) or self.offer.block_id != self.block_id:
            raise InvalidValueError("key starter offer must belong to its block")
        expected = (*self.offer.projected_starter_ids, *self.offer.candidate_ids)
        if (
            not isinstance(self.players, tuple)
            or any(not isinstance(player, PlayerState) for player in self.players)
            or tuple(player.player_id for player in self.players) != expected
        ):
            raise InvalidValueError("captured players must match forecast and candidates in order")
        selected = self.offer.selected_player_id is not None
        if selected != (self.selected_after is not None) or (selected and self.omitted):
            raise InvalidValueError("a selection needs its command order and is never omitted")
        if self.selected_after is not None and (
            type(self.selected_after) is not int or self.selected_after < 0
        ):
            raise InvalidValueError("selection order must be a non-negative decision count")
        if type(self.omitted) is not bool:
            raise InvalidValueError("omission must be a boolean")

    @property
    def selected_player(self) -> PlayerId | None:
        return None if self.offer is None else self.offer.selected_player_id

    def select(self, fixture_id: FixtureId, player_id: PlayerId, decisions: int) -> KeyStarterEntry:
        """Record the single choice of an open offer; later attempts never replace it."""
        offer = self.offer
        if offer is None or self.omitted or offer.fixture_id != fixture_id:
            raise InvalidKeyStarterError("there is no open starter offer for that fixture")
        if offer.selected_player_id is not None:
            raise KeyStarterAlreadySelectedError("the starter offer already has a selection")
        if player_id not in offer.candidate_ids:
            raise InvalidKeyStarterError("the player is not one of the captured candidates")
        return replace(
            self, offer=replace(offer, selected_player_id=player_id), selected_after=decisions
        )

    def close(self) -> KeyStarterEntry:
        """Close the block: an unselected offer becomes durably omitted."""
        if self.offer is None or self.selected_player is not None:
            return self
        return replace(self, omitted=True)

    def reopened(self) -> KeyStarterEntry:
        """The captured offer as it was on entry, before any selection or closure."""
        if self.offer is None:
            return self
        return replace(
            self,
            offer=replace(self.offer, selected_player_id=None),
            selected_after=None,
            omitted=False,
        )


def encode_entry(entry: KeyStarterEntry) -> dict[str, object]:
    offer = entry.offer
    return {
        "block_id": entry.block_id.value,
        "offer": None
        if offer is None
        else {
            "fixture_id": offer.fixture_id.value,
            "date": offer.date.isoformat(),
            "candidate_ids": [player.value for player in offer.candidate_ids],
            "opponent_id": offer.opponent_id.value,
            "competition_id": offer.competition_id.value,
            "venue": offer.venue,
            "key_match_label": offer.key_match_label,
            "projected_starter_ids": [player.value for player in offer.projected_starter_ids],
            "selected_player_id": None
            if offer.selected_player_id is None
            else offer.selected_player_id.value,
        },
        "players": _encode(entry.players),
        "selected_after": entry.selected_after,
        "omitted": entry.omitted,
    }


def decode_entry(value: object) -> KeyStarterEntry:
    if not isinstance(value, dict) or set(value) != _ENTRY_KEYS:
        raise InvalidValueError("invalid key starter entry")
    try:
        players = _decode(value["players"])
        raw_offer = value["offer"]
        offer = None if raw_offer is None else _decode_offer(value["block_id"], raw_offer)
        return KeyStarterEntry(
            BlockId(_text(value["block_id"])),
            offer,
            cast("tuple[PlayerState, ...]", players),
            cast("int | None", value["selected_after"]),
            cast("bool", value["omitted"]),
        )
    except (TypeError, ValueError) as error:
        raise InvalidValueError("invalid key starter entry") from error


def _decode_offer(block_id: object, value: object) -> KeyStarterOffer:
    if not isinstance(value, dict) or set(value) != _OFFER_KEYS:
        raise InvalidValueError("invalid key starter offer")
    raw_date = _text(value["date"])
    if date.fromisoformat(raw_date).isoformat() != raw_date:
        raise InvalidValueError("noncanonical key starter date")
    selected = value["selected_player_id"]
    label = value["key_match_label"]
    if label is not None and not isinstance(label, str):
        raise InvalidValueError("invalid key match label")
    return KeyStarterOffer(
        BlockId(_text(block_id)),
        FixtureId(_text(value["fixture_id"])),
        date.fromisoformat(raw_date),
        _players(value["candidate_ids"]),
        ClubSeasonId(_text(value["opponent_id"])),
        CompetitionId(_text(value["competition_id"])),
        cast("Literal['home', 'away', 'neutral']", value["venue"]),
        label,
        _players(value["projected_starter_ids"]),
        None if selected is None else PlayerId(_text(selected)),
    )


def _players(value: object) -> tuple[PlayerId, ...]:
    if not isinstance(value, list):
        raise InvalidValueError("player IDs must be a list")
    return tuple(PlayerId(_text(item)) for item in value)


def _text(value: object) -> str:
    if not isinstance(value, str):
        raise InvalidValueError("expected a string")
    return value
