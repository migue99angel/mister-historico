"""Lossless JSON encoding for the immutable published Catalog language.

Each dataclass and enum carries a tag because several effect DTOs share the same fields.
Only classes already defined in the published API or shared content IDs may be decoded.
"""

from dataclasses import fields, is_dataclass
from datetime import date
from enum import Enum
from typing import Any

from mister.catalog.application import api
from mister.catalog.application.api import PlayableSeasonDTO
from mister.shared_kernel import ids
from mister.shared_kernel.errors import InvalidValueError

type JsonValue = bool | int | str | list[JsonValue] | dict[str, JsonValue] | None


def _registered_classes() -> tuple[dict[str, type[Any]], dict[str, type[Enum]]]:
    dataclasses: dict[str, type[Any]] = {}
    enums: dict[str, type[Enum]] = {}
    for module in (api, ids):
        for name, candidate in vars(module).items():
            if not isinstance(candidate, type) or candidate.__module__ != module.__name__:
                continue
            if is_dataclass(candidate):
                dataclasses[name] = candidate
            elif issubclass(candidate, Enum):
                enums[name] = candidate
    return dataclasses, enums


_DATACLASSES, _ENUMS = _registered_classes()


def _encode(value: object) -> JsonValue:
    if isinstance(value, Enum):
        if type(value).__name__ not in _ENUMS:
            raise InvalidValueError(f"unregistered enum {type(value).__name__}")
        return {"$enum": type(value).__name__, "value": str(value.value)}
    if isinstance(value, date):
        return {"$date": value.isoformat()}
    if is_dataclass(value) and not isinstance(value, type):
        name = type(value).__name__
        if name not in _DATACLASSES:
            raise InvalidValueError(f"unregistered dataclass {name}")
        return {
            "$type": name,
            "fields": {field.name: _encode(getattr(value, field.name)) for field in fields(value)},
        }
    if isinstance(value, tuple):
        return [_encode(item) for item in value]
    if value is None or isinstance(value, (bool, int, str)):
        return value
    raise InvalidValueError(f"cannot encode {type(value).__name__} in catalog snapshot")


def _decode(value: JsonValue) -> object:
    if isinstance(value, list):
        return tuple(_decode(item) for item in value)
    if isinstance(value, dict):
        if set(value) == {"$date"}:
            raw_date = value["$date"]
            if not isinstance(raw_date, str):
                raise InvalidValueError("invalid snapshot date")
            return date.fromisoformat(raw_date)
        if set(value) == {"$enum", "value"}:
            name, raw_value = value["$enum"], value["value"]
            if not isinstance(name, str) or not isinstance(raw_value, str):
                raise InvalidValueError("invalid snapshot enum")
            enum_type = _ENUMS.get(name)
            if enum_type is None:
                raise InvalidValueError(f"unknown snapshot enum {name}")
            return enum_type(raw_value)
        if set(value) == {"$type", "fields"}:
            name, raw_fields = value["$type"], value["fields"]
            if not isinstance(name, str) or not isinstance(raw_fields, dict):
                raise InvalidValueError("invalid snapshot dataclass")
            data_type = _DATACLASSES.get(name)
            if data_type is None:
                raise InvalidValueError(f"unknown snapshot dataclass {name}")
            if not all(isinstance(key, str) for key in raw_fields):
                raise InvalidValueError("snapshot fields need string names")
            return data_type(**{key: _decode(item) for key, item in raw_fields.items()})
        raise InvalidValueError("invalid snapshot object")
    return value


def encode_season(season: PlayableSeasonDTO) -> dict[str, JsonValue]:
    """Produce a JSONB-compatible tree with explicit type tags."""
    encoded = _encode(season)
    if not isinstance(encoded, dict):  # pragma: no cover - the root is a dataclass
        raise InvalidValueError("invalid season snapshot")
    return encoded


def decode_season(payload: dict[str, JsonValue]) -> PlayableSeasonDTO:
    """Restore a published season without guessing effect union members."""
    decoded = _decode(payload)
    if not isinstance(decoded, PlayableSeasonDTO):
        raise InvalidValueError("snapshot does not contain a playable season")
    return decoded
