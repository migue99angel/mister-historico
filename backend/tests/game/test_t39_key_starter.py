"""T3.9 key starter in Game: durable offer, selection command, closure and replay."""

from dataclasses import dataclass, replace
from datetime import UTC, date, datetime

import pytest
from tests.contracts.suites.expected_test_fc import build_expected_test_fc_season

from mister.catalog.application.api import PlayableSeasonDTO, PlayableSeasonSummaryDTO
from mister.game.application import ports
from mister.game.application.block_codec import decode_block
from mister.game.application.closure import _simulation_request
from mister.game.application.key_starter_flow import (
    InvalidKeyStarterError,
    KeyStarterAlreadySelectedError,
    KeyStarterEntry,
)
from mister.game.application.replay import ReplayRun
from mister.game.application.rules import RulesConfiguration
from mister.game.application.use_cases import (
    AdvanceBlock,
    GetRun,
    IdempotencyConflictError,
    RunSnapshot,
    SelectKeyStarter,
    StartRun,
    TakeDecision,
)
from mister.game.domain.errors import InvalidRunTransitionError
from mister.game.infrastructure.catalog_adapter import CatalogRunContentAdapter
from mister.game.infrastructure.in_memory.run_repository import InMemoryRunStore, InMemoryUnitOfWork
from mister.game.infrastructure.in_memory.run_tokens import FakeRunTokenGenerator
from mister.game.infrastructure.in_memory.season_simulator import ScriptedSeasonSimulator
from mister.game.infrastructure.security.run_tokens import Sha256RunTokenHasher
from mister.game.infrastructure.simulation_adapter import SimulationServiceAdapter
from mister.shared_kernel.clock import FixedClock
from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.events import InMemoryEventBus
from mister.shared_kernel.ids import BlockId, FixtureId, PlayableSeasonId, PlayerId, RunId
from mister.shared_kernel.seed import Seed
from mister.simulation.application.api import SimulationService

RUN_ID = RunId.parse("00000000-0000-4000-8000-000000000159")
SUPER_FINAL = FixtureId("tfc-super-final")
SUPER_FINAL_DAY = date(2000, 8, 20)
LIGA_05 = FixtureId("tfc-liga-05")


class _Provider:
    def __init__(self, season: PlayableSeasonDTO) -> None:
        self.season = season

    def get_playable_season(self, season_id: PlayableSeasonId) -> PlayableSeasonDTO:
        return self.season

    def list_playable_seasons(self) -> tuple[PlayableSeasonSummaryDTO, ...]:
        return ()


class _Spy(SimulationServiceAdapter):
    """Real engine adapter that records every block request."""

    def __init__(self) -> None:
        super().__init__(SimulationService())
        self.requests: list[ports.BlockSimulationRequest] = []

    def simulate_block(self, request: ports.BlockSimulationRequest) -> ports.BlockSimulationResult:
        self.requests.append(request)
        return super().simulate_block(request)


@dataclass
class _Game:
    store: InMemoryRunStore
    start: StartRun
    get: GetRun
    take: TakeDecision
    advance: AdvanceBlock
    select: SelectKeyStarter
    replay: ReplayRun
    simulator: _Spy
    run_id: RunId = RUN_ID
    token: str = ""

    def snapshot(self) -> RunSnapshot:
        return RunSnapshot.decode(self.store.runs[self.run_id].snapshot)

    def version(self) -> int:
        return self.store.runs[self.run_id].version

    def entry(self) -> KeyStarterEntry:
        entries = self.snapshot().key_starters
        assert entries is not None
        return entries[-1]

    def decide_all(self) -> None:
        snapshot = self.snapshot()
        captured = CatalogRunContentAdapter.restore_game(
            self.store.runs[self.run_id].replay_inputs.content, RulesConfiguration.a_profile()
        )
        block = captured.blocks[snapshot.run.block_index]
        for index, dilemma in enumerate(block.dilemmas):
            if dilemma.id in snapshot.run.pending_dilemmas:
                self.take.execute(
                    self.run_id,
                    self.token,
                    f"decide-{block.id}-{index}",
                    self.version(),
                    dilemma.id,
                    dilemma.options[0].id,
                )

    def advance_block(self, key: str | None = None) -> None:
        self.decide_all()
        self.advance.execute(
            self.run_id, self.token, key or f"advance-{self.version()}", self.version()
        )

    def choose(self, player: PlayerId, key: str = "select-001") -> None:
        offer = self.entry().offer
        assert offer is not None
        self.select.execute(self.run_id, self.token, key, self.version(), offer.fixture_id, player)


def _game(*, offers: bool = True, simulator: ports.SeasonSimulator | None = None) -> _Game:
    season = build_expected_test_fc_season()
    content = CatalogRunContentAdapter(_Provider(season))
    store = InMemoryRunStore()
    uow = InMemoryUnitOfWork(store)
    clock = FixedClock(datetime(2026, 10, 29, tzinfo=UTC))
    hasher = Sha256RunTokenHasher()
    bus = InMemoryEventBus()
    spy = _Spy()
    engine = simulator or spy
    restore = CatalogRunContentAdapter.restore_game
    game = _Game(
        store,
        StartRun(
            uow=uow,
            capture_game=content.capture_game,
            clock=clock,
            event_bus=bus,
            token_generator=FakeRunTokenGenerator(),
            token_hasher=hasher,
            seed_factory=lambda: Seed(159),
            run_id_factory=lambda: RUN_ID,
            rules=RulesConfiguration.a_profile(),
            simulator=engine if offers else None,
        ),
        GetRun(uow=uow, token_hasher=hasher, restore_game=restore),
        TakeDecision(
            uow=uow, clock=clock, event_bus=bus, token_hasher=hasher, restore_game=restore
        ),
        AdvanceBlock(
            uow=uow,
            clock=clock,
            event_bus=bus,
            token_hasher=hasher,
            restore_game=restore,
            simulator=engine,
        ),
        SelectKeyStarter(uow=uow, clock=clock, token_hasher=hasher, restore_game=restore),
        ReplayRun(uow=uow, token_hasher=hasher, restore_game=restore, simulator=engine),
        spy,
    )
    game.token = game.start.execute(season.id).token
    return game


# --------------------------------------------------------------------------- offer


def test_a_new_run_captures_one_offer_for_the_first_key_fixture_of_the_first_block() -> None:
    game = _game()
    entry = game.entry()
    record = game.store.runs[game.run_id]
    captured = CatalogRunContentAdapter.restore_game(
        record.replay_inputs.content, RulesConfiguration.a_profile()
    )
    request = _simulation_request(
        game.snapshot(), captured, captured.blocks[0], RulesConfiguration.a_profile()
    )
    projection = SimulationServiceAdapter(SimulationService()).project_lineup(request, SUPER_FINAL)

    assert projection is not None
    offer = entry.offer
    assert offer is not None
    assert (offer.block_id, offer.fixture_id, offer.date) == (
        captured.blocks[0].id,
        SUPER_FINAL,
        SUPER_FINAL_DAY,
    )
    assert offer.projected_starter_ids == projection.starter_ids
    assert offer.candidate_ids == projection.reserve_ids[:3]
    assert offer.selected_player_id is None
    assert offer.key_match_label == "Partido clave"
    fixture = next(f for f in captured.fixtures if f.id == SUPER_FINAL.value)
    assert (offer.opponent_id, offer.competition_id, offer.venue) == (
        fixture.opponent,
        fixture.competition_id,
        fixture.venue,
    )


def test_the_offer_captures_the_entry_state_of_forecast_and_candidates() -> None:
    game = _game()
    entry = game.entry()
    assert entry.offer is not None
    players = {p.player_id: p for p in game.snapshot().run.run_state.players}

    assert tuple(p.player_id for p in entry.players) == (
        *entry.offer.projected_starter_ids,
        *entry.offer.candidate_ids,
    )
    assert all(p == players[p.player_id] for p in entry.players)


def test_a_block_without_key_fixtures_has_no_offer_and_advances_as_before() -> None:
    game = _game()
    game.advance_block()

    entry = game.entry()
    assert entry.block_id.value == "b2"
    assert entry.offer is None
    game.advance_block()
    assert game.entry().offer is not None
    assert game.entry().offer.fixture_id == LIGA_05  # type: ignore[union-attr]


def test_no_offer_is_created_without_a_projected_eleven() -> None:
    simulator = ScriptedSeasonSimulator()
    simulator.script_projection(BlockId("b1"), SUPER_FINAL, None)
    game = _game(simulator=simulator)

    assert game.entry().offer is None


def test_no_offer_is_created_with_fewer_than_two_reserves() -> None:
    simulator = ScriptedSeasonSimulator()
    eleven = tuple(PlayerId(f"tfc-{i:02}") for i in range(1, 12))
    simulator.script_projection(
        BlockId("b1"), SUPER_FINAL, ports.LineupProjection(eleven, (PlayerId("tfc-12"),))
    )
    game = _game(simulator=simulator)

    assert game.entry().offer is None


def test_runs_started_without_the_feature_keep_the_legacy_snapshot_format() -> None:
    game = _game(offers=False)

    assert game.store.runs[game.run_id].snapshot["format_version"] == 1
    assert game.snapshot().key_starters is None
    game.advance_block()
    assert game.snapshot().key_starters is None
    assert game.simulator.requests[-1].key_starter is None


# --------------------------------------------------------------------------- selection


def test_selecting_a_candidate_records_it_once_and_increments_the_version() -> None:
    game = _game()
    candidate = game.entry().offer.candidate_ids[1]  # type: ignore[union-attr]

    view = game.select.execute(game.run_id, game.token, "select-001", 0, SUPER_FINAL, candidate)

    assert view.version == 1
    assert game.entry().offer.selected_player_id == candidate  # type: ignore[union-attr]
    assert game.entry().selected_after == 0
    assert view.key_starters == game.snapshot().key_starters


def test_the_same_selection_command_replays_its_original_reply_without_writes() -> None:
    game = _game()
    candidate = game.entry().offer.candidate_ids[0]  # type: ignore[union-attr]
    first = game.select.execute(game.run_id, game.token, "select-001", 0, SUPER_FINAL, candidate)
    stored = game.store.runs[game.run_id]

    again = game.select.execute(game.run_id, game.token, "select-001", 0, SUPER_FINAL, candidate)

    assert again == first
    assert game.store.runs[game.run_id] == stored


def test_a_key_reused_with_another_body_or_command_is_a_conflict() -> None:
    game = _game()
    first, second = game.entry().offer.candidate_ids[:2]  # type: ignore[union-attr]
    game.select.execute(game.run_id, game.token, "select-001", 0, SUPER_FINAL, first)

    with pytest.raises(IdempotencyConflictError):
        game.select.execute(game.run_id, game.token, "select-001", 0, SUPER_FINAL, second)
    with pytest.raises(IdempotencyConflictError):
        game.advance.execute(game.run_id, game.token, "select-001", 0)


def test_a_selection_cannot_reuse_the_key_of_a_decision() -> None:
    game = _game()
    snapshot = game.snapshot()
    dilemma = snapshot.run.pending_dilemmas[0]
    captured = CatalogRunContentAdapter.restore_game(
        game.store.runs[game.run_id].replay_inputs.content, RulesConfiguration.a_profile()
    )
    option = next(d for d in captured.blocks[0].dilemmas if d.id == dilemma).options[0].id
    game.take.execute(game.run_id, game.token, "shared-key", 0, dilemma, option)

    with pytest.raises(IdempotencyConflictError):
        game.select.execute(
            game.run_id,
            game.token,
            "shared-key",
            0,
            SUPER_FINAL,
            game.entry().offer.candidate_ids[0],  # type: ignore[union-attr]
        )


def test_a_stale_version_is_a_concurrency_conflict() -> None:
    game = _game()
    game.decide_all()

    with pytest.raises(ports.ConcurrencyError):
        game.select.execute(
            game.run_id,
            game.token,
            "select-001",
            0,
            SUPER_FINAL,
            game.entry().offer.candidate_ids[0],  # type: ignore[union-attr]
        )


def test_a_fresh_second_selection_is_rejected() -> None:
    game = _game()
    first, second = game.entry().offer.candidate_ids[:2]  # type: ignore[union-attr]
    game.choose(first)

    with pytest.raises(KeyStarterAlreadySelectedError):
        game.select.execute(game.run_id, game.token, "select-002", 1, SUPER_FINAL, second)
    assert game.entry().offer.selected_player_id == first  # type: ignore[union-attr]


@pytest.mark.parametrize("which", ["starter", "unknown", "fixture"])
def test_invalid_candidates_and_fixtures_are_rejected(which: str) -> None:
    game = _game()
    offer = game.entry().offer
    assert offer is not None
    fixture, player = {
        "starter": (SUPER_FINAL, offer.projected_starter_ids[0]),
        "unknown": (SUPER_FINAL, PlayerId("nobody")),
        "fixture": (LIGA_05, offer.candidate_ids[0]),
    }[which]

    with pytest.raises(InvalidKeyStarterError):
        game.select.execute(game.run_id, game.token, "select-001", 0, fixture, player)
    assert game.version() == 0


def test_a_block_without_offer_rejects_any_selection() -> None:
    game = _game()
    previous = game.entry().offer
    assert previous is not None
    game.advance_block()

    with pytest.raises(InvalidKeyStarterError):
        game.select.execute(
            game.run_id,
            game.token,
            "select-late",
            game.version(),
            SUPER_FINAL,
            previous.candidate_ids[0],
        )


def test_legacy_runs_reject_selections() -> None:
    game = _game(offers=False)

    with pytest.raises(InvalidKeyStarterError):
        game.select.execute(
            game.run_id, game.token, "select-001", 0, SUPER_FINAL, PlayerId("tfc-01")
        )


def test_a_selection_is_rejected_after_the_run_finished() -> None:
    game = _game()
    for _ in range(5):
        game.advance_block()

    with pytest.raises(InvalidRunTransitionError):
        game.select.execute(
            game.run_id, game.token, "select-end", game.version(), LIGA_05, PlayerId("tfc-01")
        )


def test_dilemmas_and_the_selection_can_be_resolved_in_any_order() -> None:
    game = _game()
    candidate = game.entry().offer.candidate_ids[0]  # type: ignore[union-attr]
    game.choose(candidate)

    with pytest.raises(InvalidRunTransitionError):
        game.advance.execute(game.run_id, game.token, "advance-early", game.version())
    game.decide_all()
    assert game.entry().selected_after == 0


def test_a_wrong_token_is_rejected_before_the_body() -> None:
    game = _game()

    with pytest.raises(Exception, match="token"):
        game.select.execute(game.run_id, "wrong", "select-001", 0, SUPER_FINAL, PlayerId("nobody"))


def test_an_invalid_idempotency_key_is_a_validation_error() -> None:
    game = _game()

    with pytest.raises(InvalidValueError):
        game.select.execute(game.run_id, game.token, "short", 0, SUPER_FINAL, PlayerId("x"))


# --------------------------------------------------------------------------- closure


def test_advancing_with_a_selection_requires_the_player_only_in_that_fixture() -> None:
    game = _game()
    candidate = game.entry().offer.candidate_ids[0]  # type: ignore[union-attr]
    game.choose(candidate)

    game.advance_block()

    request = game.simulator.requests[-1]
    assert request.key_starter == ports.KeyStarterSelection(SUPER_FINAL, SUPER_FINAL_DAY, candidate)
    outcome = decode_block(game.snapshot().run.block_records[0].payload).key_starter_outcome
    assert outcome is not None
    assert (outcome.fixture_id, outcome.player_id) == (SUPER_FINAL, candidate)
    assert (candidate in outcome.starter_ids) == (outcome.absence_reason is None)


def test_advancing_without_a_selection_skips_the_offer_durably() -> None:
    game = _game()

    game.advance_block()

    entries = game.snapshot().key_starters
    assert entries is not None
    assert entries[0].omitted is True
    assert entries[0].offer is not None
    assert entries[0].offer.selected_player_id is None
    assert game.simulator.requests[-1].key_starter is None
    assert decode_block(game.snapshot().run.block_records[0].payload).key_starter_outcome is None


def test_an_omitted_offer_simulates_exactly_like_a_legacy_run() -> None:
    with_offers, legacy = _game(), _game(offers=False)

    with_offers.advance_block()
    legacy.advance_block()

    assert with_offers.snapshot().run == legacy.snapshot().run


def test_a_selection_after_closing_the_block_is_not_retroactive() -> None:
    game = _game()
    candidate = game.entry().offer.candidate_ids[0]  # type: ignore[union-attr]
    game.advance_block()

    with pytest.raises(InvalidKeyStarterError):
        game.select.execute(
            game.run_id, game.token, "select-late", game.version(), SUPER_FINAL, candidate
        )


def test_a_selection_and_an_advance_racing_on_one_version_have_a_single_winner() -> None:
    game = _game()
    game.decide_all()
    version = game.version()
    candidate = game.entry().offer.candidate_ids[0]  # type: ignore[union-attr]
    game.advance.execute(game.run_id, game.token, "advance-wins", version)

    with pytest.raises(ports.ConcurrencyError):
        game.select.execute(
            game.run_id, game.token, "select-loses", version, SUPER_FINAL, candidate
        )


def test_the_selection_survives_reload_and_the_next_block_offer_is_independent() -> None:
    game = _game()
    candidate = game.entry().offer.candidate_ids[0]  # type: ignore[union-attr]
    game.choose(candidate)
    game.advance_block()
    game.advance_block()

    entries = game.get.execute(game.run_id, game.token).key_starters
    assert entries is not None
    assert [e.block_id.value for e in entries] == ["b1", "b2", "b3"]
    assert entries[0].offer is not None
    assert entries[0].offer.selected_player_id == candidate
    assert entries[0].omitted is False
    assert entries[2].offer is not None
    assert entries[2].offer.selected_player_id is None


def test_mismatched_engine_evidence_is_rejected() -> None:
    game = _game()
    candidate = game.entry().offer.candidate_ids[0]  # type: ignore[union-attr]
    game.choose(candidate)

    class Liar(_Spy):
        def simulate_block(
            self, request: ports.BlockSimulationRequest
        ) -> ports.BlockSimulationResult:
            return replace(super().simulate_block(request), key_starter_outcome=None)

    game.advance = replace_simulator(game, Liar())
    game.decide_all()
    with pytest.raises(InvalidValueError):
        game.advance.execute(game.run_id, game.token, "advance-liar", game.version())


def replace_simulator(game: _Game, simulator: ports.SeasonSimulator) -> AdvanceBlock:
    uow = InMemoryUnitOfWork(game.store)
    return AdvanceBlock(
        uow=uow,
        clock=FixedClock(datetime(2026, 10, 29, tzinfo=UTC)),
        event_bus=InMemoryEventBus(),
        token_hasher=Sha256RunTokenHasher(),
        restore_game=CatalogRunContentAdapter.restore_game,
        simulator=simulator,
    )


# --------------------------------------------------------------------------- replay


def test_replay_reproduces_selections_omissions_and_evidence() -> None:
    game = _game()
    candidate = game.entry().offer.candidate_ids[0]  # type: ignore[union-attr]
    game.choose(candidate)
    game.advance_block()
    game.advance_block()
    game.advance_block()
    game.choose(game.entry().offer.candidate_ids[1])  # type: ignore[union-attr]

    result = game.replay.execute(game.run_id, game.token)

    assert result.verified is True
    assert result.reconstructed == game.snapshot()


def test_replay_uses_the_stored_offer_without_projecting_again() -> None:
    game = _game()
    game.advance_block()
    calls = len(game.simulator.requests)

    class NoProjection(_Spy):
        def project_lineup(
            self, request: ports.BlockSimulationRequest, fixture_id: FixtureId
        ) -> ports.LineupProjection | None:
            raise AssertionError("replay must reuse captured offers")

    replay = ReplayRun(
        uow=InMemoryUnitOfWork(game.store),
        token_hasher=Sha256RunTokenHasher(),
        restore_game=CatalogRunContentAdapter.restore_game,
        simulator=NoProjection(),
    )

    assert replay.execute(game.run_id, game.token).verified is True
    assert len(game.simulator.requests) == calls


def test_replay_rejects_tampered_evidence() -> None:
    game = _game()
    game.choose(game.entry().offer.candidate_ids[0])  # type: ignore[union-attr]
    game.advance_block()
    record = game.store.runs[game.run_id]
    snapshot = game.snapshot()
    block = snapshot.run.block_records[0]
    result = decode_block(block.payload)
    assert result.key_starter_outcome is not None
    forged = replace(
        result,
        key_starter_outcome=replace(
            result.key_starter_outcome, starter_ids=result.key_starter_outcome.starter_ids[::-1]
        ),
    )
    from mister.game.application.block_codec import encode_block  # noqa: PLC0415

    run = replace(
        snapshot.run,
        block_records=(
            replace(block, payload=encode_block(forged)),
            *snapshot.run.block_records[1:],
        ),
    )
    game.store.runs[game.run_id] = replace(record, snapshot=replace(snapshot, run=run).encode())

    with pytest.raises(InvalidValueError):
        game.replay.execute(game.run_id, game.token)


def test_legacy_runs_replay_without_interaction() -> None:
    game = _game(offers=False)
    game.advance_block()

    assert game.replay.execute(game.run_id, game.token).verified is True


# --------------------------------------------------------------------------- snapshot


def test_the_snapshot_round_trips_its_key_starter_entries() -> None:
    game = _game()
    game.choose(game.entry().offer.candidate_ids[0])  # type: ignore[union-attr]
    encoded = game.store.runs[game.run_id].snapshot

    assert encoded["format_version"] == 2
    assert RunSnapshot.decode(encoded).encode() == encoded


@pytest.mark.parametrize("version", [0, 3, "2"])
def test_an_unknown_snapshot_format_fails_explicitly(version: object) -> None:
    game = _game()
    encoded = dict(game.store.runs[game.run_id].snapshot)
    encoded["format_version"] = version

    with pytest.raises(InvalidValueError):
        RunSnapshot.decode(encoded)


def test_a_format_two_snapshot_needs_its_entries() -> None:
    game = _game()
    encoded = dict(game.store.runs[game.run_id].snapshot)
    del encoded["key_starters"]

    with pytest.raises(InvalidValueError):
        RunSnapshot.decode(encoded)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda e: {**e, "extra": 1},
        lambda e: {**e, "omitted": "no"},
        lambda e: {**e, "selected_after": -1},
        lambda e: {**e, "offer": {**e["offer"], "candidate_ids": ["tfc-01"]}},
        lambda e: {**e, "offer": {**e["offer"], "date": "20-08-2000"}},
        lambda e: {**e, "players": []},
    ],
)
def test_corrupted_entries_are_rejected(mutate: object) -> None:
    game = _game()
    encoded = dict(game.store.runs[game.run_id].snapshot)
    entries = list(encoded["key_starters"])  # type: ignore[call-overload]
    entries[0] = mutate(entries[0])  # type: ignore[operator]
    encoded["key_starters"] = entries

    with pytest.raises(InvalidValueError):
        RunSnapshot.decode(encoded)
