"""Invariants of the Sharing DTOs and the behaviour specific to its fake."""

from dataclasses import replace

import pytest
from tests.contracts.suites.share_card_renderer import make_card

from mister.shared_kernel.errors import InvalidValueError
from mister.sharing.application.ports import VerdictKind
from mister.sharing.infrastructure.in_memory.share_card import FakeShareCardRenderer


@pytest.mark.parametrize("score", [-1, 101])
def test_a_card_score_is_between_0_and_100(score: int) -> None:
    with pytest.raises(InvalidValueError, match="score"):
        replace(make_card(), mister_score=score)


def test_the_fake_renderer_needs_no_imaging_library() -> None:
    renderer = FakeShareCardRenderer()

    assert isinstance(renderer.render(make_card()), bytes)


def test_the_verdict_kinds_are_the_ones_of_the_api() -> None:
    assert {kind.value for kind in VerdictKind} == {
        "surpassed_history",
        "matched_history",
        "below_history",
        "sacked",
    }
