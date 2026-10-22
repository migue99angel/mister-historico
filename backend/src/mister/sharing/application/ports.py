"""Application ports of the Sharing context, with the card DTO.

`ShareCardRenderer` turns a `ShareCard` into the PNG of the Open Graph image (ADR-010: 1200x630,
generic crest, no real logos). The renderer must be a pure function of the card, so the same
card always yields the same bytes and the image URL can be immutable and CDN-cacheable.
"""

from dataclasses import dataclass
from typing import Protocol

from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import RunId

MAX_SCORE = 100


@dataclass(frozen=True, slots=True)
class ShareCardComparison:
    """The own result against the real one in a competition, already as display text."""

    competition_name: str
    user_result: str
    historical_result: str


@dataclass(frozen=True, slots=True)
class ShareCard:
    """Everything printed on the share image. Texts are already localised."""

    run_id: RunId
    club_name: str
    historical_manager: str
    verdict_kind: str
    verdict_text: str
    mister_score: int
    comparisons: tuple[ShareCardComparison, ...]
    share_url: str
    primary_color: str
    secondary_color: str
    alias: str | None = None

    def __post_init__(self) -> None:
        if not 0 <= self.mister_score <= MAX_SCORE:
            raise InvalidValueError(f"score must be between 0 and {MAX_SCORE}")


class ShareCardRenderer(Protocol):
    """Renders the share card as PNG bytes."""

    def render(self, card: ShareCard) -> bytes: ...
