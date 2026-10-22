"""The closed product-event DTO: unknown names, referrer limits and no IP."""

from dataclasses import fields
from datetime import datetime

import pytest

from mister.analytics.application.ports import ProductEvent, ProductEventName
from mister.analytics.infrastructure.in_memory.product_events import InMemoryProductEventSink
from mister.shared_kernel.errors import InvalidValueError
from tests.contracts.suites.product_event_sink import T0


def test_the_event_names_are_exactly_the_six_of_the_product_metrics() -> None:
    assert {name.value for name in ProductEventName} == {
        "season_viewed",
        "run_started",
        "decision_taken",
        "run_finished",
        "share_clicked",
        "shared_link_opened",
    }


def test_an_unknown_event_name_is_rejected() -> None:
    with pytest.raises(ValueError, match="not a valid ProductEventName"):
        ProductEventName("page_scrolled")


def test_an_event_carries_no_ip_nor_persistent_identifier() -> None:
    names = {field.name for field in fields(ProductEvent)}

    assert names == {"name", "occurred_at", "season_id", "run_id", "referrer"}


def test_the_referrer_is_at_most_255_characters_and_not_blank() -> None:
    with pytest.raises(InvalidValueError, match="referrer"):
        ProductEvent(ProductEventName.SEASON_VIEWED, T0, referrer="r" * 256)
    with pytest.raises(InvalidValueError, match="referrer"):
        ProductEvent(ProductEventName.SEASON_VIEWED, T0, referrer="   ")
    assert ProductEvent(ProductEventName.SEASON_VIEWED, T0, referrer="r" * 255)


def test_the_event_time_must_be_timezone_aware() -> None:
    with pytest.raises(InvalidValueError, match="timezone"):
        ProductEvent(ProductEventName.SEASON_VIEWED, datetime(2026, 10, 22))  # noqa: DTZ001


def test_the_fake_sink_exposes_what_it_recorded() -> None:
    sink = InMemoryProductEventSink()
    event = ProductEvent(ProductEventName.RUN_STARTED, T0)

    sink.record(event)

    assert sink.events == [event]
