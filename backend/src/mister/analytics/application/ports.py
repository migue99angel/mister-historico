"""Application ports of the Analytics context, with the closed event DTO (T7.3).

Privacy by construction: `ProductEvent` has no field for an IP address, a user agent or any
persistent identifier, so no sink can store one. `run_id` and `season_id` identify a game, not a
person (runs are anonymous and have no account). Event names are a closed enum: an unknown name
cannot even be built, which is how the API rejects it.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import PlayableSeasonId, RunId

MAX_REFERRER_LENGTH = 255


class ProductEventName(StrEnum):
    SEASON_VIEWED = "season_viewed"
    RUN_STARTED = "run_started"
    DECISION_TAKEN = "decision_taken"
    RUN_FINISHED = "run_finished"
    SHARE_CLICKED = "share_clicked"
    SHARED_LINK_OPENED = "shared_link_opened"


@dataclass(frozen=True, slots=True)
class ProductEvent:
    """An anonymous product event. `referrer` is a host such as `twitter.com`."""

    name: ProductEventName
    occurred_at: datetime
    season_id: PlayableSeasonId | None = None
    run_id: RunId | None = None
    referrer: str | None = None

    def __post_init__(self) -> None:
        if self.occurred_at.tzinfo is None or self.occurred_at.utcoffset() is None:
            raise InvalidValueError("occurred_at must be a timezone-aware datetime")
        if self.referrer is not None and not (
            self.referrer.strip() and len(self.referrer) <= MAX_REFERRER_LENGTH
        ):
            raise InvalidValueError(
                f"referrer must be non-blank and at most {MAX_REFERRER_LENGTH} characters"
            )


class ProductEventSink(Protocol):
    """Where product events go (a database table in production)."""

    def record(self, event: ProductEvent) -> None: ...
