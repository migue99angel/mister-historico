"""T3.9 guards: entry invariants, strict decoding, snapshot coherence and command races."""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime
from threading import Barrier
from typing import Any

import pytest
from tests.game.test_t39_key_starter import SUPER_FINAL, _Game, _game, _Spy
from tests.game.test_t39_key_starter_presentation import _api

from mister.game.application import ports
from mister.game.application.api import GameApi, InvalidKeyStarterError
from mister.game.application.key_starter_flow import (
    InvalidKeyStarterError as FlowInvalidKeyStarterError,
)
from mister.game.application.key_starter_flow import KeyStarterEntry, decode_entry, encode_entry
from mister.game.application.use_cases import (
    IdempotencyConflictError,
    RunSnapshot,
    SelectKeyStarter,
    TakeDecision,
)
from mister.game.infrastructure.catalog_adapter import CatalogRunContentAdapter
from mister.game.infrastructure.in_memory.run_repository import InMemoryUnitOfWork
from mister.game.infrastructure.security.run_tokens import Sha256RunTokenHasher
from mister.shared_kernel.clock import FixedClock
from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import BlockId, PlayerId, RunId

# --------------------------------------------------------------------------- entry invariants


def _entry() -> KeyStarterEntry:
    return _game().entry()


@pytest.mark.parametrize(
    "change",
    [
        lambda e: replace(e, block_id="b1"),
        lambda e: KeyStarterEntry(e.block_id, None, e.players),
        lambda e: replace(e, block_id=BlockId("b2")),
        lambda e: replace(e, players=e.players[::-1]),
        lambda e: replace(e, players=(*e.players[:-1], object())),
        lambda e: replace(e, selected_after=0),
        lambda e: replace(
            e,
            offer=replace(e.offer, selected_player_id=e.offer.candidate_ids[0]),
            selected_after=-1,
        ),
        lambda e: replace(
            e,
            offer=replace(e.offer, selected_player_id=e.offer.candidate_ids[0]),
            selected_after=0,
            omitted=True,
        ),
        lambda e: replace(e, omitted=1),
    ],
)
def test_an_entry_rejects_incoherent_captures(change: Callable[[Any], object]) -> None:
    entry = _entry()

    with pytest.raises(InvalidValueError):
        change(entry)


def test_an_omitted_offer_no_longer_accepts_a_selection() -> None:
    entry = _entry().close()
    assert entry.offer is not None

    with pytest.raises(FlowInvalidKeyStarterError):
        entry.select(SUPER_FINAL, entry.offer.candidate_ids[0], 0)


# --------------------------------------------------------------------------- strict decoding


@pytest.mark.parametrize(
    "mutate",
    [
        lambda e: {**e, "offer": {**e["offer"], "extra": 1}},
        lambda e: {**e, "offer": "offer"},
        lambda e: {**e, "offer": {**e["offer"], "date": "20000820"}},
        lambda e: {**e, "offer": {**e["offer"], "key_match_label": 7}},
        lambda e: {**e, "offer": {**e["offer"], "candidate_ids": "tfc-12"}},
        lambda e: {**e, "offer": {**e["offer"], "fixture_id": 1}},
        lambda e: {**e, "block_id": None},
    ],
)
def test_a_stored_entry_is_decoded_strictly(mutate: Callable[[Any], object]) -> None:
    encoded = encode_entry(_entry())

    with pytest.raises(InvalidValueError):
        decode_entry(mutate(encoded))


def test_a_stored_entry_round_trips() -> None:
    entry = _entry()

    assert decode_entry(encode_entry(entry)) == entry


# --------------------------------------------------------------------------- snapshot coherence


def _encoded(game: _Game) -> dict[str, Any]:
    return dict(game.store.runs[game.run_id].snapshot)


def test_a_format_two_snapshot_cannot_have_an_empty_interaction() -> None:
    encoded = _encoded(_game())
    encoded["key_starters"] = []

    with pytest.raises(InvalidValueError):
        RunSnapshot.decode(encoded)


def test_entries_must_follow_the_entered_blocks() -> None:
    game = _game()
    encoded = _encoded(game)
    encoded["key_starters"] = [
        *encoded["key_starters"],
        encode_entry(KeyStarterEntry(BlockId("b2"))),
    ]

    with pytest.raises(InvalidValueError):
        RunSnapshot.decode(encoded)


def test_a_closed_block_offer_must_be_selected_or_omitted() -> None:
    game = _game()
    game.advance_block()
    encoded = _encoded(game)
    entries = list(encoded["key_starters"])
    entries[0] = {**entries[0], "omitted": False}
    encoded["key_starters"] = entries

    with pytest.raises(InvalidValueError, match="selected or omitted"):
        RunSnapshot.decode(encoded)


def test_an_open_block_offer_cannot_be_omitted() -> None:
    encoded = _encoded(_game())
    encoded["key_starters"] = [{**encoded["key_starters"][0], "omitted": True}]

    with pytest.raises(InvalidValueError, match="cannot be omitted"):
        RunSnapshot.decode(encoded)


def test_a_selection_cannot_claim_decisions_that_were_never_taken() -> None:
    game = _game()
    game.choose(game.entry().offer.candidate_ids[0])  # type: ignore[union-attr]
    encoded = _encoded(game)
    encoded["key_starters"] = [{**encoded["key_starters"][0], "selected_after": 9}]

    with pytest.raises(InvalidValueError, match="never taken"):
        RunSnapshot.decode(encoded)


def test_a_legacy_snapshot_has_no_entry_to_replace() -> None:
    snapshot = _game(offers=False).snapshot()

    with pytest.raises(FlowInvalidKeyStarterError):
        snapshot.with_key_starter(KeyStarterEntry(BlockId("b1")))


# --------------------------------------------------------------------------- closure


def test_evidence_for_a_selection_that_was_never_made_is_rejected() -> None:
    game = _game()

    class Inventor(_Spy):
        def simulate_block(
            self, request: ports.BlockSimulationRequest
        ) -> ports.BlockSimulationResult:
            result = super().simulate_block(request)
            match = result.matches[0]
            return replace(
                result,
                key_starter_outcome=ports.KeyStarterOutcome(
                    match.fixture_id, match.date, PlayerId("tfc-01"), (PlayerId("tfc-01"),)
                ),
            )

    from tests.game.test_t39_key_starter import replace_simulator  # noqa: PLC0415

    advance = replace_simulator(game, Inventor())
    game.decide_all()
    with pytest.raises(InvalidValueError, match="never selected"):
        advance.execute(game.run_id, game.token, "advance-invented", game.version())


# --------------------------------------------------------------------------- command


def test_an_unknown_run_cannot_select() -> None:
    game = _game()

    with pytest.raises(ports.RunNotFoundError):
        game.select.execute(
            RunId.parse("00000000-0000-4000-8000-000000000999"),
            game.token,
            "select-001",
            0,
            SUPER_FINAL,
            PlayerId("x"),
        )


def test_a_negative_version_is_a_validation_error() -> None:
    game = _game()

    with pytest.raises(InvalidValueError):
        game.select.execute(game.run_id, game.token, "select-001", -1, SUPER_FINAL, PlayerId("x"))


def test_a_composition_without_the_command_rejects_selections() -> None:
    game = _game()
    api = _api(game)
    bare = GameApi(
        start_run=game.start,
        get_run=game.get,
        take_decision=game.take,
        advance_block=game.advance,
        uow=InMemoryUnitOfWork(game.store),
        token_hasher=Sha256RunTokenHasher(),
        presentation=api._presentation,
        seasons=api._seasons,
    )

    with pytest.raises(InvalidKeyStarterError):
        bare.select_key_starter(
            game.run_id, game.token, "select-001", 0, SUPER_FINAL, PlayerId("x")
        )


def _racing_selects(game: _Game) -> tuple[SelectKeyStarter, SelectKeyStarter]:
    barrier = Barrier(2)

    class RacingUnitOfWork(InMemoryUnitOfWork):
        def commit(self) -> None:
            barrier.wait(timeout=5)
            super().commit()

    def build() -> SelectKeyStarter:
        return SelectKeyStarter(
            uow=RacingUnitOfWork(game.store),
            clock=FixedClock(datetime(2026, 10, 29, tzinfo=UTC)),
            token_hasher=Sha256RunTokenHasher(),
            restore_game=CatalogRunContentAdapter.restore_game,
        )

    return build(), build()


def test_a_double_tap_with_one_key_returns_the_single_winning_reply() -> None:
    game = _game()
    candidate = game.entry().offer.candidate_ids[0]  # type: ignore[union-attr]
    left, right = _racing_selects(game)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(s.execute, game.run_id, game.token, "double-tap", 0, SUPER_FINAL, candidate)
            for s in (left, right)
        ]
        views = [future.result(timeout=10) for future in futures]

    assert views[0] == views[1]
    assert game.version() == 1


def test_a_race_with_one_key_and_two_bodies_has_one_winner_and_a_conflict() -> None:
    game = _game()
    first, second = game.entry().offer.candidate_ids[:2]  # type: ignore[union-attr]
    left, right = _racing_selects(game)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(s.execute, game.run_id, game.token, "same-key", 0, SUPER_FINAL, player)
            for s, player in ((left, first), (right, second))
        ]
        outcomes: list[object] = []
        for future in futures:
            try:
                outcomes.append(future.result(timeout=10))
            except IdempotencyConflictError as error:
                outcomes.append(error)

    assert sum(isinstance(item, IdempotencyConflictError) for item in outcomes) == 1
    assert game.version() == 1


def test_the_decision_command_keeps_working_with_the_interaction() -> None:
    game = _game()
    assert isinstance(game.take, TakeDecision)
    game.decide_all()

    assert game.entry().offer is not None
    assert game.snapshot().run.pending_dilemmas == ()
