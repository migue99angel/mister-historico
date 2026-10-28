"""Strict, versioned codec for complete Game block simulation results."""

from __future__ import annotations

import json

from mister.game.application.ports import BlockSimulationResult
from mister.game.application.run_codec import _decode, _encode, assert_format1_schema_supported
from mister.shared_kernel.errors import InvalidValueError

_FORMAT_VERSION = 1


class BlockSimulationCodec:
    """Serialize all simulation output, preserving absent versus empty unresolved data."""

    @staticmethod
    def encode(value: BlockSimulationResult) -> bytes:
        assert_format1_schema_supported()
        if not isinstance(value, BlockSimulationResult):
            raise InvalidValueError("BlockSimulationCodec.encode requires BlockSimulationResult")
        envelope = {"format_version": _FORMAT_VERSION, "result": _encode(value)}
        return json.dumps(
            envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode("utf-8")

    @staticmethod
    def decode(payload: bytes) -> BlockSimulationResult:
        assert_format1_schema_supported()
        if not isinstance(payload, bytes):
            raise InvalidValueError("block simulation payload must be bytes")
        try:
            value = json.loads(
                payload.decode("utf-8"),
                object_pairs_hook=_unique_object,
                parse_constant=_invalid_constant,
            )
            canonical = json.dumps(
                value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
            ).encode("utf-8")
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError) as error:
            raise InvalidValueError("invalid block simulation encoding") from error
        if (
            canonical != payload
            or not isinstance(value, dict)
            or set(value) != {"format_version", "result"}
        ):
            raise InvalidValueError("noncanonical or invalid block simulation envelope")
        if type(value["format_version"]) is not int or value["format_version"] != _FORMAT_VERSION:
            raise InvalidValueError("unsupported block simulation format")
        result = _decode(value["result"])
        if not isinstance(result, BlockSimulationResult):
            raise InvalidValueError("block simulation payload has an unknown result type")
        return result


def encode_block(value: BlockSimulationResult) -> bytes:
    return BlockSimulationCodec.encode(value)


def decode_block(payload: bytes) -> BlockSimulationResult:
    return BlockSimulationCodec.decode(payload)


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _invalid_constant(token: str) -> object:
    raise ValueError(f"invalid JSON constant {token}")
