"""Opaque, immutable copy of the playable content captured for one run."""

import hashlib
import json
from dataclasses import dataclass

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
        if type(self.format_version) is not int or self.format_version != 1:
            raise InvalidValueError(f"unsupported run content format {self.format_version}")
        if not isinstance(self.content_json, str):
            raise InvalidValueError("content_json must be a string")
        if not isinstance(self.playable_season_id, PlayableSeasonId):
            raise InvalidValueError("run content needs a typed playable season identity")
        try:
            root = json.loads(
                self.content_json,
                object_pairs_hook=_unique_object,
                parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
            )
            canonical = json.dumps(
                root, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
            )
        except (json.JSONDecodeError, TypeError, ValueError) as error:
            raise InvalidValueError("run content must be finite canonical JSON") from error
        if not isinstance(root, dict):
            raise InvalidValueError("run content must be a canonical JSON object")
        if canonical != self.content_json:
            raise InvalidValueError("run content JSON must use canonical encoding")
        expected = hashlib.sha256(self.content_json.encode("utf-8")).hexdigest()
        if self.digest != expected:
            raise InvalidValueError("run content digest does not match canonical bytes")


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key}")
        result[key] = value
    return result
