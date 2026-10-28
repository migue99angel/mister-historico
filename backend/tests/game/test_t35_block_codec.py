import json
from dataclasses import replace

import pytest
from tests.contracts.suites.game_samples import make_simulation_result

from mister.game.application.block_codec import BlockSimulationCodec, decode_block, encode_block
from mister.shared_kernel.errors import InvalidValueError


def test_block_codec_round_trips_full_result_and_distinguishes_unknown_ties_from_empty() -> None:
    result = make_simulation_result()
    decoded = decode_block(encode_block(result))
    assert decoded == result
    assert decoded.matches[0].extra_time == result.matches[0].extra_time
    assert decoded.matches[0].penalties == result.matches[0].penalties
    assert decoded.unresolved_knockout_ties == result.unresolved_knockout_ties
    assert (
        BlockSimulationCodec.decode(
            BlockSimulationCodec.encode(replace(result, unresolved_knockout_ties=None))
        ).unresolved_knockout_ties
        is None
    )
    assert (
        BlockSimulationCodec.decode(
            BlockSimulationCodec.encode(replace(result, unresolved_knockout_ties=()))
        ).unresolved_knockout_ties
        == ()
    )


def test_block_codec_rejects_unknown_format_version() -> None:
    with pytest.raises(InvalidValueError):
        BlockSimulationCodec.decode(b'{"format_version":99,"type":"block_simulation_result"}')


def test_block_codec_rejects_noncanonical_bytes_and_wrong_typed_fields() -> None:
    payload = BlockSimulationCodec.encode(make_simulation_result())
    with pytest.raises(InvalidValueError):
        BlockSimulationCodec.decode(b" " + payload)
    envelope = json.loads(payload)
    encoded_result = envelope["result"]
    match = encoded_result["fields"]["matches"]["$tuple"][0]
    match["fields"]["key"] = 1
    corrupted = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()
    with pytest.raises(InvalidValueError, match="field types"):
        BlockSimulationCodec.decode(corrupted)


@pytest.mark.parametrize(
    "payload",
    [
        "not bytes",
        b"\xff",
        b"{",
        b'{"format_version":1,"format_version":1,"result":null}',
        b'{"format_version":1,"result":NaN}',
        b'{"extra":0,"format_version":1,"result":null}',
        b'{"format_version":true,"result":null}',
        b'{"format_version":99,"result":null}',
        b'{"format_version":1,"result":42}',
    ],
)
def test_block_codec_rejects_invalid_payload_shapes_and_versions(payload: object) -> None:
    with pytest.raises(InvalidValueError):
        decode_block(payload)  # type: ignore[arg-type]


def test_block_codec_rejects_values_other_than_complete_results() -> None:
    with pytest.raises(InvalidValueError, match="requires BlockSimulationResult"):
        encode_block(object())  # type: ignore[arg-type]
