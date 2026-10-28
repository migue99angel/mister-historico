"""Immutable JSON-shaped values returned by the published Game facade."""

from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite
from types import MappingProxyType
from typing import cast

type JsonScalar = str | int | float | bool | None
type JsonValue = JsonScalar | tuple[JsonValue, ...] | Mapping[str, JsonValue]


def _freeze(value: object) -> JsonValue:
    if value is None or type(value) in (str, int, float, bool):
        if isinstance(value, float) and not isfinite(value):
            raise TypeError("JSON numbers must be finite")
        return cast("JsonScalar", value)
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise TypeError("JSON object keys must be strings")
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    raise TypeError(f"unsupported JSON value: {type(value).__name__}")


def _thaw(value: JsonValue) -> object:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


@dataclass(frozen=True, slots=True, init=False)
class Presented:
    """A detached response tree containing no domain or persistence objects."""

    value: Mapping[str, JsonValue]

    def __init__(self, value: Mapping[str, object]) -> None:
        frozen = _freeze(value)
        if not isinstance(frozen, Mapping):
            raise TypeError("presented value must be a JSON object")
        object.__setattr__(self, "value", frozen)

    def to_json(self) -> dict[str, object]:
        """Return a fresh JSON object for HTTP serialization."""
        return cast("dict[str, object]", _thaw(self.value))


@dataclass(frozen=True, slots=True)
class Started:
    """Public start response with the sole token disclosure point."""

    run_token: str
    view: Presented

    def to_json(self) -> dict[str, object]:
        return {"runToken": self.run_token, "run": self.view.to_json()}
