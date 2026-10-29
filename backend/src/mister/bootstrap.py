"""Composition root: the only place that wires ports to adapters (PLAN §3.2).

It is the only module allowed to import `mister.*.infrastructure`.
"""

import secrets
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import sqlalchemy as sa

from mister.catalog.application.load_catalog import LoadCatalog
from mister.catalog.application.load_types import CatalogLoadUnavailableError
from mister.catalog.application.ratings_tool import RatingsTool
from mister.catalog.application.validate_content import ValidateContent
from mister.catalog.infrastructure.content_schema.rating_sheets import YamlRatingSheetStore
from mister.catalog.infrastructure.sqlalchemy.catalog import SqlSeasonContentProvider
from mister.catalog.infrastructure.sqlalchemy.publisher import SqlCatalogPublisher
from mister.catalog.infrastructure.yaml_validation import YamlContentValidator
from mister.game.application.api import GameApi
from mister.game.application.rules import RulesConfiguration
from mister.game.application.use_cases import AdvanceBlock, GetRun, StartRun, TakeDecision
from mister.game.infrastructure.catalog_adapter import CatalogRunContentAdapter
from mister.game.infrastructure.presentation_adapter import CatalogPresentationAdapter
from mister.game.infrastructure.security.run_tokens import (
    SecretsRunTokenGenerator,
    Sha256RunTokenHasher,
)
from mister.game.infrastructure.simulation_adapter import SimulationServiceAdapter
from mister.game.infrastructure.sqlalchemy.uow import SqlUnitOfWork
from mister.settings import Settings
from mister.shared_kernel.clock import SystemClock
from mister.shared_kernel.events import InMemoryEventBus
from mister.shared_kernel.seed import Seed
from mister.simulation.application.api import SimulationService


@dataclass(frozen=True, slots=True)
class GameRuntime:
    engine: sa.Engine
    settings: Settings

    def api(self) -> GameApi:
        uow = SqlUnitOfWork(self.engine)
        hasher = Sha256RunTokenHasher()
        provider = SqlSeasonContentProvider(self.engine)
        content = CatalogRunContentAdapter(provider)
        rules = RulesConfiguration.a_profile()
        presentation = CatalogPresentationAdapter(provider, self.settings)
        clock, bus = SystemClock(), InMemoryEventBus()
        start = StartRun(
            uow=uow,
            capture_game=content.capture_game,
            clock=clock,
            event_bus=bus,
            token_generator=SecretsRunTokenGenerator(),
            token_hasher=hasher,
            seed_factory=lambda: Seed(secrets.randbits(64)),
            rules=rules,
        )
        get = GetRun(
            uow=uow,
            token_hasher=hasher,
            restore_game=content.restore_game,
        )
        take = TakeDecision(
            uow=uow,
            clock=clock,
            event_bus=bus,
            token_hasher=hasher,
            restore_game=content.restore_game,
        )
        advance = AdvanceBlock(
            uow=uow,
            clock=clock,
            event_bus=bus,
            token_hasher=hasher,
            restore_game=content.restore_game,
            simulator=SimulationServiceAdapter(SimulationService()),
        )
        return GameApi(
            start_run=start,
            get_run=get,
            take_decision=take,
            advance_block=advance,
            uow=uow,
            token_hasher=hasher,
            presentation=presentation,
            seasons=presentation,
        )


@dataclass(frozen=True, slots=True)
class Container:
    settings: Settings
    engine: sa.Engine | None = None

    def api(self) -> GameApi:
        if self.engine is None:
            raise RuntimeError("Game API runtime has no database engine")
        return GameRuntime(self.engine, self.settings).api()


def bootstrap(settings: Settings | None = None) -> Container:
    configured = settings if settings is not None else Settings()
    return Container(configured, sa.create_engine(configured.database_url))


def build_ratings_tool(content_root: Path) -> RatingsTool:
    """The ratings use case over the YAML content under `content_root` (used by the CLI)."""
    return RatingsTool(YamlRatingSheetStore(content_root))


def build_validate_content(content_root: Path) -> ValidateContent:
    """Wire the content validation use case to the root-bound YAML adapter."""
    return ValidateContent(YamlContentValidator(content_root))


@contextmanager
def build_load_catalog(database_url: str | None = None) -> Iterator[LoadCatalog]:
    """Wire the SQL publisher for one command and release its engine afterwards."""
    url = database_url if database_url is not None else Settings().database_url
    try:
        engine = sa.create_engine(url)
    except (sa.exc.SQLAlchemyError, ValueError) as error:
        raise CatalogLoadUnavailableError("database configuration unavailable") from error
    try:
        yield LoadCatalog(SqlCatalogPublisher(engine))
    finally:
        engine.dispose()
