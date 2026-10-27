from datetime import UTC, datetime

import pytest

from mister.game.domain.events import (
    BlockSimulated,
    DecisionTaken,
    ManagerSacked,
    RunFinished,
    RunStarted,
)
from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.events import DomainEvent
from mister.shared_kernel.ids import PlayableSeasonId, RunId
from mister.shared_kernel.seed import Seed


def test_run_lifecycle_events_are_frozen_domain_events() -> None:
    now = datetime(2000, 1, 1, tzinfo=UTC)
    event = RunStarted(
        occurred_at=now, run_id=RunId.new(), season_id=PlayableSeasonId("test-season"), seed=Seed(1)
    )

    assert event.occurred_at == now
    with pytest.raises(AttributeError):
        event.run_id = RunId.new()  # type: ignore[misc]


def test_all_events_require_timezone_aware_timestamp() -> None:
    with pytest.raises(InvalidValueError):
        RunFinished(occurred_at=datetime(2000, 1, 1), run_id=RunId.new())


@pytest.mark.parametrize("event_type", [DecisionTaken, BlockSimulated, ManagerSacked, RunFinished])
def test_lifecycle_events_inherit_shared_domain_event(event_type: type[object]) -> None:
    assert issubclass(event_type, DomainEvent)
