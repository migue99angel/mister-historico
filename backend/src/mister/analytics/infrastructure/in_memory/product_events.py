"""In-memory `ProductEventSink`."""

from mister.analytics.application.ports import ProductEvent


class InMemoryProductEventSink:
    """Keeps the recorded events, in order, in `events`."""

    def __init__(self) -> None:
        self.events: list[ProductEvent] = []

    def record(self, event: ProductEvent) -> None:
        self.events.append(event)
