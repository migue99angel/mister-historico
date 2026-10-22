"""Contract of the `ShareCardRenderer` port.

Reuse: subclass `ShareCardRendererContract` and override `make_renderer` (T5.3 returns the
Pillow renderer).
"""

import struct
import uuid
from collections.abc import Callable
from dataclasses import replace

import pytest

from mister.shared_kernel.ids import RunId
from mister.sharing.application.ports import (
    ShareCard,
    ShareCardComparison,
    ShareCardRenderer,
    VerdictKind,
)

RendererFactory = Callable[[], ShareCardRenderer]

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
CARD_WIDTH = 1200
CARD_HEIGHT = 630


def make_card() -> ShareCard:
    return ShareCard(
        run_id=RunId(uuid.UUID(int=1)),
        club_name="Test FC",
        historical_manager="Mister Ficticio",
        verdict_kind=VerdictKind.SURPASSED_HISTORY,
        verdict_text="You surpassed Mister Ficticio.",
        mister_score=78,
        comparisons=(
            ShareCardComparison("Liga Test", user_result="Champion", historical_result="Runner-up"),
            ShareCardComparison("Copa Test", user_result="Final", historical_result="Champion"),
        ),
        share_url="https://misterhistorico.example/r/00000000-0000-0000-0000-000000000001",
        primary_color="#1F4E79",
        secondary_color="#FFFFFF",
        alias="Mister Test",
    )


class ShareCardRendererContract:
    """Behaviour every `ShareCardRenderer` must have."""

    @pytest.fixture
    def make_renderer(self) -> RendererFactory:
        raise NotImplementedError

    def test_the_output_is_a_png(self, make_renderer: RendererFactory) -> None:
        assert make_renderer().render(make_card()).startswith(PNG_SIGNATURE)

    def test_the_image_is_1200_by_630(self, make_renderer: RendererFactory) -> None:
        png = make_renderer().render(make_card())

        # IHDR is the first chunk: 8-byte signature, 4-byte length, b"IHDR", width, height.
        assert png[12:16] == b"IHDR"
        assert struct.unpack(">II", png[16:24]) == (CARD_WIDTH, CARD_HEIGHT)

    def test_the_same_card_always_gives_the_same_bytes(
        self, make_renderer: RendererFactory
    ) -> None:
        renderer = make_renderer()

        assert renderer.render(make_card()) == renderer.render(make_card())
        assert make_renderer().render(make_card()) == renderer.render(make_card())

    def test_a_different_card_gives_different_bytes(self, make_renderer: RendererFactory) -> None:
        renderer = make_renderer()

        other = replace(make_card(), mister_score=12, verdict_kind=VerdictKind.BELOW_HISTORY)

        assert renderer.render(make_card()) != renderer.render(other)

    def test_a_card_without_alias_or_comparisons_renders(
        self, make_renderer: RendererFactory
    ) -> None:
        bare = replace(make_card(), alias=None, comparisons=())

        assert make_renderer().render(bare).startswith(PNG_SIGNATURE)

    def test_very_long_texts_still_render(self, make_renderer: RendererFactory) -> None:
        long_card = replace(
            make_card(), club_name="X" * 500, verdict_text="Y" * 2000, historical_manager="Z" * 500
        )

        assert make_renderer().render(long_card).startswith(PNG_SIGNATURE)
