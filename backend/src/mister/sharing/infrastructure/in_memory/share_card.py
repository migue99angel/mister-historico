"""Fake `ShareCardRenderer`: deterministic PNG bytes, no imaging library.

It writes a valid, solid-colour 1200x630 PNG (standard library only: `zlib` and `struct`). The
colour is derived from a hash of the whole card, so equal cards give equal bytes and different
cards give different bytes, which is all the callers of the port can rely on.
"""

import hashlib
import struct
import zlib

from mister.sharing.application.ports import ShareCard

WIDTH = 1200
HEIGHT = 630
_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _chunk(kind: bytes, data: bytes) -> bytes:
    body = kind + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))


class FakeShareCardRenderer:
    """Solid-colour PNG whose colour depends on the card."""

    def render(self, card: ShareCard) -> bytes:
        red, green, blue = hashlib.sha256(repr(card).encode()).digest()[:3]
        row = b"\x00" + bytes((red, green, blue)) * WIDTH  # filter type 0 + RGB pixels
        header = struct.pack(">IIBBBBB", WIDTH, HEIGHT, 8, 2, 0, 0, 0)  # 8-bit truecolour
        return (
            _SIGNATURE
            + _chunk(b"IHDR", header)
            + _chunk(b"IDAT", zlib.compress(row * HEIGHT, 9))
            + _chunk(b"IEND", b"")
        )
