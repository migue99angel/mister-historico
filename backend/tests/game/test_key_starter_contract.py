"""Published starter DTOs reject ambiguous captures and false participation evidence."""

from dataclasses import FrozenInstanceError
from datetime import date, datetime
from types import ModuleType

import pytest

from mister.game.application import ports
from mister.game.infrastructure.simulation_mapping import (
    from_key_starter_outcome,
    to_key_starter_selection,
)
from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import BlockId, ClubSeasonId, CompetitionId, FixtureId, PlayerId
from mister.simulation.application import api

DAY = date(2000, 9, 3)
PLAYER = PlayerId("test-player")
FIXTURE = FixtureId("test-fixture")
OTHER = PlayerId("other-player")
BLOCK = BlockId("block-1")


def _offer(
    candidates: tuple[PlayerId, ...] = (PLAYER, OTHER),
    selected: PlayerId | None = None,
    block: BlockId = BLOCK,
) -> ports.KeyStarterOffer:
    return ports.KeyStarterOffer(
        block,
        FIXTURE,
        DAY,
        candidates,
        ClubSeasonId("test-rovers-2000-01"),
        CompetitionId("liga-test"),
        "home",
        "Derbi de prueba",
        selected,
    )


def test_offer_captures_candidates_and_selection_without_mutation() -> None:
    offer = _offer()
    assert offer.selected_player_id is None
    with pytest.raises(FrozenInstanceError):
        offer.fixture_id = FixtureId("other")  # type: ignore[misc]


@pytest.mark.parametrize("candidates", [(), (PLAYER, PLAYER), [PLAYER]])
def test_offer_requires_nonempty_distinct_immutable_candidates(candidates: object) -> None:
    with pytest.raises(InvalidValueError):
        _offer(candidates)  # type: ignore[arg-type]


def test_offer_rejects_selection_outside_captured_candidates() -> None:
    with pytest.raises(InvalidValueError):
        _offer(selected=PlayerId("outsider"))


@pytest.mark.parametrize("module", [ports, api])
def test_selection_requires_typed_identity_and_exact_date(module: ModuleType) -> None:
    selection = module.KeyStarterSelection
    assert selection(FIXTURE, DAY, PLAYER).player_id == PLAYER
    for values in [
        ("test-fixture", DAY, PLAYER),
        (FIXTURE, datetime(2000, 9, 3), PLAYER),
        (FIXTURE, DAY, "test-player"),
    ]:
        with pytest.raises(InvalidValueError):
            selection(*values)


@pytest.mark.parametrize("module", [ports, api])
def test_application_proves_participation_or_explains_absence(module: ModuleType) -> None:
    outcome = module.KeyStarterOutcome
    assert outcome(FIXTURE, DAY, PLAYER, (PLAYER,)).absence_reason is None
    fallback = PlayerId("fallback")
    assert outcome(FIXTURE, DAY, PLAYER, (fallback,), "injured").starter_ids == (fallback,)
    assert outcome(FIXTURE, DAY, PLAYER, (), "fixture_not_played").starter_ids == ()
    for starters, reason in [
        ((PLAYER,), "injured"),
        ((fallback,), None),
        ((PLAYER, PLAYER), None),
        ((PLAYER,), "fixture_not_played"),
        ((), "injured"),
        ((fallback,), "unknown"),
        ([PLAYER], None),
    ]:
        with pytest.raises(InvalidValueError):
            outcome(FIXTURE, DAY, PLAYER, starters, reason)


@pytest.mark.parametrize("module", [ports, api])
def test_application_rejects_more_than_eleven_starters(module: ModuleType) -> None:
    starters = tuple(PlayerId(f"player-{i}") for i in range(12))
    with pytest.raises(InvalidValueError):
        module.KeyStarterOutcome(FIXTURE, DAY, starters[0], starters)


@pytest.mark.parametrize("module", [ports, api])
def test_application_requires_typed_starter_ids(module: ModuleType) -> None:
    with pytest.raises(InvalidValueError):
        module.KeyStarterOutcome(FIXTURE, DAY, PLAYER, ("test-player",))


def test_offer_requires_typed_block_and_candidates() -> None:
    with pytest.raises(InvalidValueError):
        _offer(block="block-1")  # type: ignore[arg-type]
    with pytest.raises(InvalidValueError):
        _offer(("player", OTHER))  # type: ignore[arg-type]
    chosen = _offer(selected=PLAYER)
    assert chosen.selected_player_id == PLAYER


def test_acl_translates_selection_without_widening_its_fixture_scope() -> None:
    source = ports.KeyStarterSelection(FIXTURE, DAY, PLAYER)
    assert to_key_starter_selection(source) == api.KeyStarterSelection(FIXTURE, DAY, PLAYER)


def test_acl_preserves_actual_starters_and_absence_reason() -> None:
    fallback = PlayerId("fallback")
    source = api.KeyStarterOutcome(FIXTURE, DAY, PLAYER, (fallback,), "not_in_squad")
    assert from_key_starter_outcome(source) == ports.KeyStarterOutcome(
        FIXTURE, DAY, PLAYER, (fallback,), "not_in_squad"
    )


@pytest.mark.parametrize("count", [1, 4])
def test_offer_limits_the_choice_to_two_or_three_candidates(count: int) -> None:
    with pytest.raises(InvalidValueError):
        _offer(tuple(PlayerId(f"candidate-{i}") for i in range(count)))
