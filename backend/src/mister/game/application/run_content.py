"""Opaque, immutable copy of the playable content captured for one run."""

from dataclasses import dataclass
import hashlib

from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import PlayableSeasonId


@dataclass(frozen=True, slots=True)
class RunContentSnapshot:
    """Canonical serialized content and its identity, version and integrity digest."""

    format_version: int
    content_json: str
    digest: str
    playable_season_id: PlayableSeasonId

    def __post_init__(self) -> None:
        if self.format_version != 1:
            raise InvalidValueError(f"unsupported run content format {self.format_version}")
        if not isinstance(self.content_json, str):
            raise InvalidValueError("content_json must be a string")
        expected = hashlib.sha256(self.content_json.encode("utf-8")).hexdigest()
        if self.digest != expected:
            raise InvalidValueError("run content digest does not match canonical bytes")
