"""Fakes of Leaderboard, Sharing, Analytics and Evaluation run against their contract suites."""

import pytest

from mister.analytics.application.ports import ProductEventSink
from mister.analytics.infrastructure.in_memory.product_events import InMemoryProductEventSink
from mister.evaluation.infrastructure.in_memory.historical_outcomes import (
    InMemoryHistoricalOutcomeProvider,
)
from mister.leaderboard.infrastructure.in_memory.leaderboard import InMemoryLeaderboardRepository
from mister.sharing.infrastructure.in_memory.share_card import FakeShareCardRenderer
from tests.contracts.suites.historical_outcome_provider import (
    HistoricalOutcomeProviderContract,
    ProviderFactory,
)
from tests.contracts.suites.leaderboard_repository import (
    LeaderboardRepositoryContract,
)
from tests.contracts.suites.leaderboard_repository import RepoFactory as LeaderboardFactory
from tests.contracts.suites.product_event_sink import (
    ProductEventSinkContract,
    ReadEvents,
    SinkFactory,
)
from tests.contracts.suites.share_card_renderer import (
    RendererFactory,
    ShareCardRendererContract,
)


class TestInMemoryLeaderboardRepository(LeaderboardRepositoryContract):
    @pytest.fixture
    def make_repo(self) -> LeaderboardFactory:
        return InMemoryLeaderboardRepository


class TestFakeShareCardRenderer(ShareCardRendererContract):
    @pytest.fixture
    def make_renderer(self) -> RendererFactory:
        return FakeShareCardRenderer


class TestInMemoryProductEventSink(ProductEventSinkContract):
    @pytest.fixture
    def make_sink(self) -> SinkFactory:
        def make() -> tuple[ProductEventSink, ReadEvents]:
            sink = InMemoryProductEventSink()
            return sink, lambda: sink.events

        return make


class TestInMemoryHistoricalOutcomeProvider(HistoricalOutcomeProviderContract):
    @pytest.fixture
    def make_provider(self) -> ProviderFactory:
        return InMemoryHistoricalOutcomeProvider
