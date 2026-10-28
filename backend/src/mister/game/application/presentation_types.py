"""Immutable JSON-shaped values returned by the published Game facade."""

from dataclasses import dataclass
from typing import Mapping, TypeAlias

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | tuple["JsonValue", ...] | Mapping[str, "JsonValue"]


@dataclass(frozen=True, slots=True)
class Presented:
    """A detached response tree containing no domain or persistence objects."""

    value: Mapping[str, JsonValue]


@dataclass(frozen=True, slots=True)
class Started:
    """Public start response with the sole token disclosure point."""

    run_token: str
    view: Presented
