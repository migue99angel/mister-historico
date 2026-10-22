"""Domain events and the in-process event bus.

The V1 bus is synchronous and in memory (PLAN §3.1): `publish` returns once every subscriber
has handled the event.
"""

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol, TypeVar, cast

from mister.shared_kernel.errors import InvalidValueError

E = TypeVar("E", bound="DomainEvent")


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    """Base of every domain event: something that already happened, at `occurred_at`.

    Subclasses are frozen, keyword-only dataclasses that add their own fields.
    """

    occurred_at: datetime

    def __post_init__(self) -> None:
        if self.occurred_at.tzinfo is None or self.occurred_at.utcoffset() is None:
            raise InvalidValueError("occurred_at must be a timezone-aware datetime")


class EventBus(Protocol):
    """Port to publish events and subscribe handlers by event type."""

    def publish(self, event: DomainEvent) -> None: ...

    def subscribe(self, event_type: type[E], handler: Callable[[E], None]) -> None: ...


class InMemoryEventBus:
    """Synchronous bus that delivers events in publication order.

    - A handler receives events whose class is `event_type` or a subclass of it, so
      subscribing to `DomainEvent` receives everything.
    - Handlers of one event run in subscription order.
    - An event published by a handler is queued and delivered after the event being handled
      has reached all its handlers, so the global order is the publication order.
    - A handler error propagates to the outermost `publish`; events still queued are dropped.
    """

    def __init__(self) -> None:
        self._subscriptions: list[tuple[type[DomainEvent], Callable[[Any], None]]] = []
        self._queue: deque[DomainEvent] = deque()
        self._dispatching = False

    def subscribe(self, event_type: type[E], handler: Callable[[E], None]) -> None:
        self._subscriptions.append((event_type, cast("Callable[[Any], None]", handler)))

    def publish(self, event: DomainEvent) -> None:
        self._queue.append(event)
        if self._dispatching:
            return
        self._dispatching = True
        try:
            while self._queue:
                current = self._queue.popleft()
                for event_type, handler in list(self._subscriptions):
                    if isinstance(current, event_type):
                        handler(current)
        finally:
            self._dispatching = False
            self._queue.clear()
