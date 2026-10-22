"""`DomainEvent` and the synchronous in-memory `EventBus`."""

from dataclasses import FrozenInstanceError, dataclass
from datetime import UTC, datetime

import pytest

from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.events import DomainEvent, EventBus, InMemoryEventBus

NOW = datetime(2012, 12, 13, tzinfo=UTC)


@dataclass(frozen=True, kw_only=True)
class RunFinished(DomainEvent):
    run: str


@dataclass(frozen=True, kw_only=True)
class RunEvaluated(DomainEvent):
    score: int


def test_domain_event_is_frozen_and_carries_occurred_at() -> None:
    event = RunFinished(occurred_at=NOW, run="r1")

    assert event.occurred_at == NOW
    with pytest.raises(FrozenInstanceError):
        event.run = "r2"  # type: ignore[misc]


def test_domain_event_rejects_naive_timestamps() -> None:
    with pytest.raises(InvalidValueError):
        RunFinished(occurred_at=datetime(2012, 12, 13), run="r1")  # noqa: DTZ001


def test_bus_delivers_events_to_a_subscriber_in_publication_order() -> None:
    bus = InMemoryEventBus()
    received: list[str] = []
    bus.subscribe(RunFinished, lambda e: received.append(e.run))

    for name in ["r1", "r2", "r3"]:
        bus.publish(RunFinished(occurred_at=NOW, run=name))

    assert received == ["r1", "r2", "r3"]


def test_bus_delivers_to_subscribers_in_subscription_order() -> None:
    bus = InMemoryEventBus()
    calls: list[str] = []
    bus.subscribe(RunFinished, lambda _: calls.append("first"))
    bus.subscribe(RunFinished, lambda _: calls.append("second"))

    bus.publish(RunFinished(occurred_at=NOW, run="r1"))

    assert calls == ["first", "second"]


def test_bus_delivers_only_to_subscribers_of_the_event_type() -> None:
    bus = InMemoryEventBus()
    finished: list[RunFinished] = []
    evaluated: list[RunEvaluated] = []
    bus.subscribe(RunFinished, finished.append)
    bus.subscribe(RunEvaluated, evaluated.append)

    bus.publish(RunEvaluated(occurred_at=NOW, score=70))

    assert finished == []
    assert [e.score for e in evaluated] == [70]


def test_subscribing_to_the_base_class_receives_every_event() -> None:
    bus = InMemoryEventBus()
    everything: list[DomainEvent] = []
    bus.subscribe(DomainEvent, everything.append)

    bus.publish(RunFinished(occurred_at=NOW, run="r1"))
    bus.publish(RunEvaluated(occurred_at=NOW, score=1))

    assert len(everything) == 2


def test_publishing_without_subscribers_does_not_fail() -> None:
    InMemoryEventBus().publish(RunFinished(occurred_at=NOW, run="r1"))


def test_events_published_by_a_handler_are_delivered_after_the_current_one() -> None:
    bus = InMemoryEventBus()
    order: list[str] = []

    def on_finished(event: RunFinished) -> None:
        order.append(f"finished:{event.run}")
        bus.publish(RunEvaluated(occurred_at=NOW, score=1))
        order.append(f"finished-done:{event.run}")

    bus.subscribe(RunFinished, on_finished)
    bus.subscribe(RunEvaluated, lambda _: order.append("evaluated"))
    bus.subscribe(RunFinished, lambda e: order.append(f"second:{e.run}"))

    bus.publish(RunFinished(occurred_at=NOW, run="r1"))

    assert order == ["finished:r1", "finished-done:r1", "second:r1", "evaluated"]


def test_a_handler_error_propagates_to_the_publisher() -> None:
    bus = InMemoryEventBus()

    def boom(_: RunFinished) -> None:
        raise RuntimeError("handler failed")

    bus.subscribe(RunFinished, boom)

    with pytest.raises(RuntimeError, match="handler failed"):
        bus.publish(RunFinished(occurred_at=NOW, run="r1"))


def test_in_memory_bus_satisfies_the_protocol() -> None:
    bus: EventBus = InMemoryEventBus()

    bus.publish(RunFinished(occurred_at=NOW, run="r1"))
