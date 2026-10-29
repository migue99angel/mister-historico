"""Strict, versioned JSON codec for the complete private Run aggregate."""

from __future__ import annotations

import base64
import hashlib
import json
import uuid
from dataclasses import fields, is_dataclass
from datetime import date, datetime
from enum import Enum
from types import UnionType
from typing import Any, Literal, TypeAliasType, Union, cast, get_args, get_origin, get_type_hints

from mister.game.application import ports
from mister.game.domain import run, squad_registry, state
from mister.shared_kernel import ids, seed
from mister.shared_kernel.errors import InvalidValueError

_FORMAT_VERSION = 1
_TUPLE_VARIADIC_ARITY = 2
_FORMAT1_SCHEMA_FINGERPRINT = "2d5d8b5068c9276a925ff1cf70b28ee24dc9bd75b930eb378fbe2112d617a521"
_TYPES = (
    run.Run,
    run.RunStatus,
    run.ClosureOutcome,
    run.DecisionOption,
    run.DilemmaDefinition,
    run.BlockDefinition,
    run.Decision,
    run.BlockRecord,
    state.RunState,
    state.Tactic,
    state.TacticStyle,
    state.Position,
    state.Priority,
    state.PlayerState,
    state.CompetitionPriority,
    state.ForcedInjury,
    squad_registry.SquadRegistry,
    squad_registry.Membership,
    squad_registry.SquadTransfer,
    ids.RunId,
    ids.PlayableSeasonId,
    ids.BlockId,
    ids.DilemmaId,
    ids.OptionId,
    ids.FixtureId,
    ids.ClubSeasonId,
    ids.PlayerId,
    ids.CompetitionId,
    seed.Seed,
    ports.BlockSimulationResult,
    ports.MatchOutcome,
    ports.ScoreLine,
    ports.TeamVenue,
    ports.UserResult,
    ports.Side,
    ports.EventKind,
    ports.InjuryOutcome,
    ports.PlayerOutcome,
    ports.BlockEvent,
    ports.StandingRow,
    ports.Standings,
    ports.UnresolvedKnockoutTie,
    ports.KeyStarterOutcome,
)
_TYPE_BY_NAME = {f"{item.__module__}.{item.__qualname__}": item for item in _TYPES}
# Optional fields added after format 1 shipped: omitted while None, so payloads written
# before them keep their exact canonical bytes. An explicit null is noncanonical.
_OMITTED_WHEN_NONE: dict[type, frozenset[str]] = {
    ports.BlockSimulationResult: frozenset({"key_starter_outcome"}),
}


def _encode(value: object) -> object:  # noqa: PLR0911 - tagged scalar formats are explicit
    if value is None or type(value) in (str, int, bool):
        return value
    if isinstance(value, bytes):
        return {"$bytes": base64.b64encode(value).decode("ascii")}
    if isinstance(value, datetime):
        return {"$datetime": value.isoformat()}
    if isinstance(value, date):
        return {"$date": value.isoformat()}
    if isinstance(value, uuid.UUID):
        return {"$uuid": str(value)}
    if isinstance(value, tuple):
        return {"$tuple": [_encode(item) for item in value]}
    if isinstance(value, Enum):
        name = f"{type(value).__module__}.{type(value).__qualname__}"
        if name not in _TYPE_BY_NAME:
            raise InvalidValueError(f"unsupported run enum {name}")
        return {"$enum": name, "value": value.value}
    if is_dataclass(value) and not isinstance(value, type):
        name = f"{type(value).__module__}.{type(value).__qualname__}"
        if name not in _TYPE_BY_NAME:
            raise InvalidValueError(f"unsupported run value {name}")
        omitted = _OMITTED_WHEN_NONE.get(type(value), frozenset())
        return {
            "$type": name,
            "fields": {
                field.name: _encode(getattr(value, field.name))
                for field in fields(value)
                if field.name not in omitted or getattr(value, field.name) is not None
            },
        }
    raise InvalidValueError(f"unsupported value in run codec: {type(value).__name__}")


def _decode(value: object) -> object:  # noqa: PLR0911, PLR0912, PLR0915 - strict tag parser
    if value is None or type(value) in (str, int, bool):
        return value
    if isinstance(value, list):
        raise InvalidValueError("untyped JSON arrays are not valid in run codec")
    if not isinstance(value, dict):
        raise InvalidValueError("invalid value in run codec")
    if set(value) == {"$bytes"}:
        raw = value["$bytes"]
        if not isinstance(raw, str):
            raise InvalidValueError("invalid encoded bytes")
        try:
            decoded = base64.b64decode(raw, validate=True)
        except ValueError as error:
            raise InvalidValueError("invalid encoded bytes") from error
        if base64.b64encode(decoded).decode("ascii") != raw:
            raise InvalidValueError("noncanonical encoded bytes")
        return decoded
    if set(value) in ({"$date"}, {"$datetime"}, {"$uuid"}):
        key = next(iter(value))
        raw = value[key]
        if not isinstance(raw, str):
            raise InvalidValueError("invalid scalar encoding")
        try:
            if key == "$date":
                parsed = date.fromisoformat(raw)
                if parsed.isoformat() != raw:
                    raise ValueError
                return parsed
            if key == "$datetime":
                parsed_dt = datetime.fromisoformat(raw)
                if parsed_dt.isoformat() != raw:
                    raise ValueError
                return parsed_dt
            parsed_uuid = uuid.UUID(raw)
            if str(parsed_uuid) != raw:
                raise ValueError
            return parsed_uuid
        except ValueError as error:
            raise InvalidValueError("invalid scalar encoding") from error
    if set(value) == {"$tuple"}:
        items = value["$tuple"]
        if not isinstance(items, list):
            raise InvalidValueError("invalid tuple encoding")
        return tuple(_decode(item) for item in items)
    if set(value) == {"$enum", "value"}:
        name, member = value["$enum"], value["value"]
        cls = _TYPE_BY_NAME.get(name) if isinstance(name, str) else None
        if cls is None or not issubclass(cls, Enum):
            raise InvalidValueError("unknown enum in run codec")
        try:
            return cast("Any", cls)(member)
        except (ValueError, TypeError) as error:
            raise InvalidValueError("unknown enum value in run codec") from error
    if set(value) == {"$type", "fields"}:
        name, raw_fields = value["$type"], value["fields"]
        cls = _TYPE_BY_NAME.get(name) if isinstance(name, str) else None
        if cls is None or not is_dataclass(cls) or not isinstance(raw_fields, dict):
            raise InvalidValueError("unknown type in run codec")
        expected = {field.name for field in fields(cls)}
        omitted = _OMITTED_WHEN_NONE.get(cls, frozenset())
        if not expected - omitted <= set(raw_fields) <= expected or any(
            raw_fields[key] is None for key in omitted & set(raw_fields)
        ):
            raise InvalidValueError("run codec fields do not match the versioned schema")
        try:
            decoded_fields = {key: _decode(item) for key, item in raw_fields.items()}
            decoded_fields.update((key, None) for key in omitted - set(raw_fields))
            hints = get_type_hints(cls)
            if any(not _matches(decoded_fields[key], hints[key]) for key in expected):
                raise InvalidValueError("run codec field types do not match the versioned schema")
            return cast("Any", cls)(**decoded_fields)
        except InvalidValueError:
            raise
        except (TypeError, ValueError) as error:
            raise InvalidValueError("invalid run codec object") from error
    raise InvalidValueError("unknown tagged value in run codec")


class RunCodec:
    """Encode/decode Runs as strict canonical JSON objects for JSONB persistence."""

    @staticmethod
    def encode(value: run.Run) -> dict[str, object]:
        assert_format1_schema_supported()
        if not isinstance(value, run.Run):
            raise InvalidValueError("RunCodec.encode requires a Run")
        return {"format_version": _FORMAT_VERSION, "aggregate": _encode(value)}

    @staticmethod
    def decode(value: object) -> run.Run:
        assert_format1_schema_supported()
        if not isinstance(value, dict) or set(value) != {"format_version", "aggregate"}:
            raise InvalidValueError("invalid run codec envelope")
        if type(value["format_version"]) is not int or value["format_version"] != _FORMAT_VERSION:
            raise InvalidValueError("unsupported run codec format")
        decoded = _decode(value["aggregate"])
        if not isinstance(decoded, run.Run):
            raise InvalidValueError("run codec payload is not a Run")
        return decoded


def encode_run(value: run.Run) -> dict[str, object]:
    return RunCodec.encode(value)


def decode_run(value: object) -> run.Run:
    return RunCodec.decode(value)


def assert_format1_schema_supported() -> None:
    """Fail loudly if a private dataclass changed without a format migration review."""
    schema: dict[str, object] = {
        name: [[field.name, str(field.type)] for field in fields(cls)]
        for name, cls in sorted(_TYPE_BY_NAME.items())
        if is_dataclass(cls)
    }
    schema["$omitted_when_none"] = [
        [f"{cls.__module__}.{cls.__qualname__}", sorted(names)]
        for cls, names in _OMITTED_WHEN_NONE.items()
    ]
    encoded = json.dumps(schema, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    if hashlib.sha256(encoded.encode("utf-8")).hexdigest() != _FORMAT1_SCHEMA_FINGERPRINT:
        raise InvalidValueError("run codec format 1 schema changed; review and version the codec")


def _matches(value: object, annotation: object) -> bool:  # noqa: PLR0911, PLR0912
    if annotation is Any or annotation is object:
        return True
    if isinstance(annotation, TypeAliasType):
        return _matches(value, annotation.__value__)
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin in (UnionType, Union):
        return any(_matches(value, option) for option in args)
    if origin is tuple:
        if not isinstance(value, tuple):
            return False
        if len(args) == _TUPLE_VARIADIC_ARITY and args[1] is Ellipsis:
            return all(_matches(item, args[0]) for item in value)
        return len(value) == len(args) and all(
            _matches(item, item_type) for item, item_type in zip(value, args, strict=True)
        )
    if origin is Literal:
        return value in args and type(value) is type(args[0])
    if annotation is int:
        return type(value) is int
    if annotation is bool:
        return type(value) is bool
    if annotation is str:
        return type(value) is str
    if annotation is bytes:
        return isinstance(value, bytes)
    if annotation is date:
        return isinstance(value, date) and not isinstance(value, datetime)
    if annotation is datetime:
        return isinstance(value, datetime)
    if isinstance(annotation, type):
        return isinstance(value, annotation)
    return False
