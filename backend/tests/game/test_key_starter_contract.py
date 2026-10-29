"""Published starter DTOs reject ambiguous captures and false participation evidence."""

from dataclasses import FrozenInstanceError
from datetime import date, datetime

import pytest

from mister.game.application import ports
from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import BlockId, FixtureId, PlayerId
from mister.simulation.application import api

DAY = date(2000, 9, 3)
PLAYER = PlayerId("test-player")
FIXTURE = FixtureId("test-fixture")


def test_offer_captures_candidates_and_selection_without_mutation() -> None:
    offer = ports.KeyStarterOffer(BlockId("block-1"), FIXTURE, DAY, (PLAYER,))
    assert offer.selected_player_id is None
    with pytest.raises(FrozenInstanceError):
        offer.fixture_id = FixtureId("other")  # type: ignore[misc]


@pytest.mark.parametrize("candidates", [(), (PLAYER, PLAYER), [PLAYER]])
def test_offer_requires_nonempty_distinct_immutable_candidates(candidates: object) -> None:
    with pytest.raises(InvalidValueError):
        ports.KeyStarterOffer(BlockId("block-1"), FIXTURE, DAY, candidates)  # type: ignore[arg-type]


def test_offer_rejects_selection_outside_captured_candidates() -> None:
    with pytest.raises(InvalidValueError):
        ports.KeyStarterOffer(BlockId("block-1"), FIXTURE, DAY, (PLAYER,), PlayerId("outsider"))


@pytest.mark.parametrize("module", [ports, api])
def test_selection_requires_typed_identity_and_exact_date(module: object) -> None:
    selection = getattr(module, "KeyStarterSelection")
    assert selection(FIXTURE, DAY, PLAYER).player_id == PLAYER
    for values in [
        ("test-fixture", DAY, PLAYER),
        (FIXTURE, datetime(2000, 9, 3), PLAYER),
        (FIXTURE, DAY, "test-player"),
    ]:
        with pytest.raises(InvalidValueError):
            selection(*values)


@pytest.mark.parametrize("module", [ports, api])
def test_application_proves_participation_or_explains_absence(module: object) -> None:
    outcome = getattr(module, "KeyStarterOutcome")
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
def test_application_rejects_more_than_eleven_starters(module: object) -> None:
    starters = tuple(PlayerId(f"player-{i}") for i in range(12))
    with pytest.raises(InvalidValueError):
        getattr(module, "KeyStarterOutcome")(FIXTURE, DAY, starters[0], starters)


@pytest.mark.parametrize("module", [ports, api])
def test_application_requires_typed_starter_ids(module: object) -> None:
    with pytest.raises(InvalidValueError):
        getattr(module, "KeyStarterOutcome")(FIXTURE, DAY, PLAYER, ("test-player",))


def test_offer_requires_typed_block_and_candidates() -> None:
    with pytest.raises(InvalidValueError):
        ports.KeyStarterOffer("block-1", FIXTURE, DAY, (PLAYER,))  # type: ignore[arg-type]
    with pytest.raises(InvalidValueError):
        ports.KeyStarterOffer(BlockId("block-1"), FIXTURE, DAY, ("player",))  # type: ignore[arg-type]
    chosen = ports.KeyStarterOffer(BlockId("block-1"), FIXTURE, DAY, (PLAYER,), PLAYER)
    assert chosen.selected_player_id == PLAYER


def test_acl_translates_selection_without_widening_its_fixture_scope() -> None:
    from mister.game.infrastructure.simulation_mapping import to_key_starter_selection

    source = ports.KeyStarterSelection(FIXTURE, DAY, PLAYER)
    assert to_key_starter_selection(source) == api.KeyStarterSelection(FIXTURE, DAY, PLAYER)


def test_acl_preserves_actual_starters_and_absence_reason() -> None:
    from mister.game.infrastructure.simulation_mapping import from_key_starter_outcome

    fallback = PlayerId("fallback")
    source = api.KeyStarterOutcome(FIXTURE, DAY, PLAYER, (fallback,), "not_in_squad")
    assert from_key_starter_outcome(source) == ports.KeyStarterOutcome(
        FIXTURE, DAY, PLAYER, (fallback,), "not_in_squad"
    )
