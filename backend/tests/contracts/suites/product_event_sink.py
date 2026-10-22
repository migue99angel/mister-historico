"""Contract of the `ProductEventSink` port.

The port can only `record`, so the suite needs to read back what a sink stored: the factory
returns the sink and a `read` callable (the fake reads its list, the Postgres adapter of T7.3
queries its table). Neither side can hold an IP address: the DTO has no such field.

Reuse: subclass `ProductEventSinkContract` and override `make_sink`.
"""

import uuid
from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta

import pytest

from mister.analytics.application.ports import ProductEvent, ProductEventName, ProductEventSink
from mister.shared_kernel.ids import PlayableSeasonId, RunId

ReadEvents = Callable[[], Sequence[ProductEvent]]
SinkFactory = Callable[[], tuple[ProductEventSink, ReadEvents]]

T0 = datetime(2026, 10, 22, 10, 0, tzinfo=UTC)
SEASON = PlayableSeasonId("test-fc-2000-01")
RUN = RunId(uuid.UUID(int=1))


class ProductEventSinkContract:
    """Behaviour every `ProductEventSink` must have."""

    @pytest.fixture
    def make_sink(self) -> SinkFactory:
        raise NotImplementedError

    def test_a_recorded_event_is_stored_unchanged(self, make_sink: SinkFactory) -> None:
        sink, read = make_sink()
        event = ProductEvent(
            ProductEventName.SHARED_LINK_OPENED, T0, season_id=SEASON, run_id=RUN, referrer="x.com"
        )

        sink.record(event)

        assert list(read()) == [event]

    def test_events_are_kept_in_the_order_they_were_recorded(self, make_sink: SinkFactory) -> None:
        sink, read = make_sink()
        events = [
            ProductEvent(ProductEventName.SEASON_VIEWED, T0, season_id=SEASON),
            ProductEvent(ProductEventName.RUN_STARTED, T0 + timedelta(seconds=1), run_id=RUN),
            ProductEvent(ProductEventName.RUN_FINISHED, T0 + timedelta(seconds=2), run_id=RUN),
        ]

        for event in events:
            sink.record(event)

        assert list(read()) == events

    def test_identical_events_are_both_kept(self, make_sink: SinkFactory) -> None:
        sink, read = make_sink()
        event = ProductEvent(ProductEventName.SHARE_CLICKED, T0, run_id=RUN)

        sink.record(event)
        sink.record(event)

        assert len(read()) == 2

    def test_an_event_without_optional_fields_is_accepted(self, make_sink: SinkFactory) -> None:
        sink, read = make_sink()
        event = ProductEvent(ProductEventName.SEASON_VIEWED, T0)

        sink.record(event)

        assert list(read()) == [event]

    def test_a_fresh_sink_has_no_events(self, make_sink: SinkFactory) -> None:
        _, read = make_sink()

        assert list(read()) == []
