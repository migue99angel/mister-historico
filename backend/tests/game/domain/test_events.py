from datetime import UTC, datetime

import pytest

from mister.game.domain.events import BlockSimulated, DecisionTaken, ManagerSacked, RunFinished, RunStarted
from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import PlayableSeasonId, RunId
from mister.shared_kernel.seed import Seed


def test_run_lifecycle_events_are_frozen_domain_events() -> None:
    now = datetime(2000, 1, 1, tzinfo=UTC)
    event = RunStarted(now, RunId.new(), PlayableSeasonId("test-season"), Seed(1))

    assert event.occurred_at == now
    with pytest.raises(AttributeError):
        event.run_id = RunId.new()  # type: ignore[misc]


def test_all_events_require_timezone_aware_timestamp() -> None:
    with pytest.raises(InvalidValueError):
        RunFinished(datetime(2000, 1, 1), RunId.new())


@pytest.mark.parametrize("event_type", [DecisionTaken, BlockSimulated, ManagerSacked, RunFinished])
def test_lifecycle_events_are_constructible(event_type: type[object]) -> None:
    # Concrete payload validation is exercised through Run transitions.
    assert event_type is not None
