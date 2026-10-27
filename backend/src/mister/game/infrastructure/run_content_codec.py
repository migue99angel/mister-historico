"""Strict, versioned codec for the public Catalog DTO graph captured by Game."""

import hashlib
import json
from dataclasses import fields, is_dataclass
from datetime import date
from enum import Enum
from types import UnionType
from typing import Any, Literal, Union, get_args, get_origin, get_type_hints

from mister.catalog.application import api as catalog
from mister.game.application.run_content import RunContentSnapshot
from mister.shared_kernel import ids
from mister.shared_kernel.errors import InvalidValueError

_DTO_NAMES = (
    "TacticDTO",
    "BlockDTO",
    "ManagerDTO",
    "GoalStatsDTO",
    "LeagueRulesDTO",
    "GroupDTO",
    "GroupStageDTO",
    "StageDTO",
    "CompetitionDTO",
    "BoardObjectiveDTO",
    "InjuryForcedEventDTO",
    "HistoricalOutcomeDTO",
    "PlayerDTO",
    "AggregateStrengthDTO",
    "RealLeagueDTO",
    "ClubSeasonDTO",
    "RealResultDTO",
    "FixtureDTO",
    "KnockoutSlotDTO",
    "KnockoutCalendarDTO",
    "GroupEntryAssignmentDTO",
    "GroupEntryAssignmentsDTO",
    "HeadToHeadFixtureDTO",
    "HeadToHeadResultDTO",
    "HeadToHeadEvidenceDTO",
    "StandingRowDTO",
    "StandingsCutoffDTO",
    "RealTieDTO",
    "MoraleEffectDTO",
    "PlayerMoraleEffectDTO",
    "SignPlayerEffectDTO",
    "SellPlayerEffectDTO",
    "SetTacticEffectDTO",
    "CompetitionPriorityEffectDTO",
    "BoardConfidenceEffectDTO",
    "YouthMinutesEffectDTO",
    "InjuryEffectDTO",
    "FitnessEffectDTO",
    "DilemmaOptionDTO",
    "DilemmaDTO",
    "TextDTO",
    "PlayableSeasonSummaryDTO",
    "PlayableSeasonDTO",
)
_ENUM_NAMES = (
    "TacticStyle",
    "Priority",
    "Position",
    "Subrole",
    "Venue",
    "CompetitionKind",
    "CompetitionTier",
    "Round",
    "Tiebreaker",
    "ObjectiveKind",
    "TextKind",
)
_ID_NAMES = (
    "BlockId",
    "ClubId",
    "ClubSeasonId",
    "CompetitionId",
    "DilemmaId",
    "FixtureId",
    "OptionId",
    "PlayableSeasonId",
    "PlayerId",
)
_DTOS = {name: getattr(catalog, name) for name in _DTO_NAMES}
_ENUMS = {name: getattr(catalog, name) for name in _ENUM_NAMES}
_IDS = {name: getattr(ids, name) for name in _ID_NAMES}
_TAGS = {value: key for key, value in _DTOS.items()}
_ENUM_TAGS = {value: key for key, value in _ENUMS.items()}
_ID_TAGS = {value: key for key, value in _IDS.items()}


def _encode(value: Any) -> Any:
    if type(value) in _ID_TAGS:
        return {"$id": _ID_TAGS[type(value)], "value": value.value}
    if type(value) in _ENUM_TAGS:
        return {"$enum": _ENUM_TAGS[type(value)], "value": value.value}
    if type(value) in _TAGS and is_dataclass(value):
        return {
            "$type": _TAGS[type(value)],
            "fields": {f.name: _encode(getattr(value, f.name)) for f in fields(value)},
        }
    if isinstance(value, Enum):
        raise InvalidValueError(f"unsupported run content enum type {type(value).__name__}")
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, date):
        return {"$date": value.isoformat()}
    if isinstance(value, tuple):
        return [_encode(item) for item in value]
    raise InvalidValueError(f"unsupported run content value type {type(value).__name__}")


def _decode(value: Any, expected: Any) -> Any:  # noqa: PLR0911, PLR0912
    origin = get_origin(expected)
    args = get_args(expected)
    if origin is Literal:
        if value not in args:
            raise InvalidValueError("value is outside the declared literal set")
        return value
    if origin in (UnionType, Union):
        if value is None and type(None) in args:
            return None
        failures: list[str] = []
        for option in args:
            if option is type(None):
                continue
            try:
                return _decode(value, option)
            except (InvalidValueError, TypeError, ValueError) as error:
                failures.append(str(error))
        raise InvalidValueError(f"JSON value does not match the declared union: {failures}")
    if origin is tuple:
        if not isinstance(value, list):
            raise InvalidValueError("expected an array in run content")
        item_type = args[0] if args else Any
        if len(args) > 1 and args[-1] is not Ellipsis:
            return tuple(_decode(item, kind) for item, kind in zip(value, args, strict=True))
        return tuple(_decode(item, item_type) for item in value)
    if expected is date:
        if not isinstance(value, dict) or set(value) != {"$date"}:
            raise InvalidValueError("invalid date tag")
        try:
            return date.fromisoformat(value["$date"])
        except (TypeError, ValueError) as error:
            raise InvalidValueError("invalid ISO date") from error
    if expected in _IDS.values():
        if (
            not isinstance(value, dict)
            or set(value) != {"$id", "value"}
            or value["$id"] != _ID_TAGS[expected]
        ):
            raise InvalidValueError("invalid or unknown ID tag")
        return expected(value["value"])
    if expected in _ENUMS.values():
        if (
            not isinstance(value, dict)
            or set(value) != {"$enum", "value"}
            or value["$enum"] != _ENUM_TAGS[expected]
        ):
            raise InvalidValueError("invalid or unknown enum tag")
        return expected(value["value"])
    if expected in _DTOS.values():
        tag = _TAGS[expected]
        if (
            not isinstance(value, dict)
            or set(value) != {"$type", "fields"}
            or value["$type"] != tag
        ):
            raise InvalidValueError(f"invalid or unknown DTO tag for {tag}")
        raw = value["fields"]
        names = {field.name for field in fields(expected)}
        if not isinstance(raw, dict) or set(raw) != names:
            raise InvalidValueError(f"fields do not match schema for {tag}")
        hints = get_type_hints(expected)
        try:
            return expected(**{name: _decode(raw[name], hints[name]) for name in names})
        except (TypeError, ValueError) as error:
            raise InvalidValueError(f"invalid fields for {tag}: {error}") from error
    if expected is Any:
        raise InvalidValueError("untyped values are not permitted in run content")
    if expected in (str, int, float, bool) and type(value) is not expected:
        raise InvalidValueError(f"expected {expected.__name__}, got {type(value).__name__}")
    if not isinstance(value, expected):
        raise InvalidValueError(f"expected {expected}, got {type(value).__name__}")
    return value


def encode_playable_season(season: catalog.PlayableSeasonDTO) -> RunContentSnapshot:
    content_json = json.dumps(
        _encode(season), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )
    return RunContentSnapshot(
        1, content_json, hashlib.sha256(content_json.encode("utf-8")).hexdigest(), season.id
    )


def decode_playable_season(snapshot: RunContentSnapshot) -> catalog.PlayableSeasonDTO:
    if snapshot.format_version != 1:
        raise InvalidValueError(f"unsupported run content format {snapshot.format_version}")
    if hashlib.sha256(snapshot.content_json.encode("utf-8")).hexdigest() != snapshot.digest:
        raise InvalidValueError("run content digest mismatch")
    try:
        raw = json.loads(
            snapshot.content_json,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
        decoded = _decode(raw, catalog.PlayableSeasonDTO)
        if not isinstance(decoded, catalog.PlayableSeasonDTO):
            raise InvalidValueError("run content root is not a playable season DTO")
        season = decoded
    except (json.JSONDecodeError, ValueError) as error:
        raise InvalidValueError(f"corrupt run content JSON: {error}") from error
    if season.id != snapshot.playable_season_id:
        raise InvalidValueError("run content identity does not match envelope")
    return season
