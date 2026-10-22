"""Invariants of the Game persistence DTOs and the errors of its ports."""

from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta

import pytest
from tests.contracts.suites.game_samples import (
    T0,
    make_decision,
    make_idempotency_record,
    make_run_record,
)

from mister.game.application.ports import (
    ConcurrencyError,
    DecisionLogRewrittenError,
    IdempotencyKeyExistsError,
    InternalError,
    NoActiveTransactionError,
    Priority,
    RunAlreadyExistsError,
    RunNotFoundError,
    TacticStyle,
    TacticSystem,
)
from mister.shared_kernel.errors import DomainError, InvalidValueError
from mister.shared_kernel.ids import RunId


def test_a_run_record_is_immutable() -> None:
    record = make_run_record()

    with pytest.raises(FrozenInstanceError):
        record.version = 2  # type: ignore[misc]


def test_a_run_starts_at_version_zero_like_the_api() -> None:
    assert make_run_record().version == 0
    with pytest.raises(InvalidValueError, match="version"):
        replace(make_run_record(), version=-1)


def test_the_token_is_stored_hashed_so_the_hash_cannot_be_blank() -> None:
    with pytest.raises(InvalidValueError, match="run_token_hash"):
        replace(make_run_record(), run_token_hash="  ")  # noqa: S106


def test_the_snapshot_must_be_json_serializable() -> None:
    with pytest.raises(InvalidValueError, match="JSON"):
        replace(make_run_record(), snapshot={"squad": {1, 2}})


def test_the_snapshot_cannot_hold_nan() -> None:
    with pytest.raises(InvalidValueError, match="JSON"):
        replace(make_run_record(), snapshot={"morale": float("nan")})


def test_timestamps_must_be_timezone_aware() -> None:
    naive = datetime(2026, 10, 22, 10, 0)
    with pytest.raises(InvalidValueError, match="timezone"):
        replace(make_run_record(), created_at=naive)
    with pytest.raises(InvalidValueError, match="timezone"):
        replace(make_run_record(), updated_at=naive)


def test_a_run_cannot_be_updated_before_it_was_created() -> None:
    with pytest.raises(InvalidValueError, match="updated_at"):
        replace(make_run_record(), updated_at=T0 - timedelta(seconds=1))


def test_decisions_are_numbered_from_one_without_gaps() -> None:
    with pytest.raises(InvalidValueError, match="sequence"):
        replace(make_run_record(), decisions=(make_decision(2),))
    with pytest.raises(InvalidValueError, match="sequence"):
        replace(make_run_record(), decisions=(make_decision(1), make_decision(3)))


def test_a_decision_timestamp_must_be_timezone_aware() -> None:
    with pytest.raises(InvalidValueError, match="timezone"):
        replace(make_decision(), decided_at=datetime(2026, 10, 22))


@pytest.mark.parametrize("length", [0, 7, 129])
def test_the_idempotency_key_has_between_8_and_128_characters(length: int) -> None:
    record = make_idempotency_record(make_run_record())

    with pytest.raises(InvalidValueError, match="key"):
        replace(record, key="k" * length)


@pytest.mark.parametrize("length", [8, 128])
def test_the_idempotency_key_limits_are_inclusive(length: int) -> None:
    record = make_idempotency_record(make_run_record())

    assert replace(record, key="k" * length).key == "k" * length


def test_idempotency_needs_a_request_hash() -> None:
    record = make_idempotency_record(make_run_record())

    with pytest.raises(InvalidValueError, match="request_hash"):
        replace(record, request_hash="")


def test_the_idempotent_response_must_be_json_serializable_and_timestamped() -> None:
    record = make_idempotency_record(make_run_record())

    with pytest.raises(InvalidValueError, match="JSON"):
        replace(record, response={"when": T0})
    with pytest.raises(InvalidValueError, match="timezone"):
        replace(record, created_at=datetime(2026, 10, 22))


@pytest.mark.parametrize(
    "error",
    [
        RunAlreadyExistsError(RunId.new()),
        DecisionLogRewrittenError(RunId.new()),
        IdempotencyKeyExistsError(RunId.new(), "idem-key-1"),
        NoActiveTransactionError(),
    ],
)
def test_errors_that_are_not_in_the_api_are_internal(error: DomainError) -> None:
    assert isinstance(error, InternalError)


@pytest.mark.parametrize(
    "error",
    [ConcurrencyError(RunId.new(), expected=0), RunNotFoundError(RunId.new())],
)
def test_errors_of_the_api_are_not_internal(error: DomainError) -> None:
    assert not isinstance(error, InternalError)


def test_the_idempotency_key_error_names_the_key() -> None:
    assert "idem-key-1" in str(IdempotencyKeyExistsError(RunId.new(), "idem-key-1"))


@pytest.mark.parametrize("system", ["4-4-2", "4-2-3-1", "3-5-2", "4-3-3"])
def test_a_tactic_system_accepts_the_canonical_formats(system: str) -> None:
    assert str(TacticSystem(system)) == system


@pytest.mark.parametrize("system", ["4-3-2", "7-2-1", "4-3", "4-4-2-0", "442", "1-1-1-1-1-5", "x"])
def test_a_tactic_system_must_add_up_to_ten_outfield_players(system: str) -> None:
    with pytest.raises(InvalidValueError, match="system"):
        TacticSystem(system)


def test_the_game_vocabulary_matches_the_api() -> None:
    assert {s.value for s in TacticStyle} == {"pressing", "counter", "possession", "balanced"}
    assert {p.value for p in Priority} == {"low", "normal", "high"}


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (ConcurrencyError(RunId.new(), expected=0), "version_conflict"),
        (RunNotFoundError(RunId.new()), "run_not_found"),
        (NoActiveTransactionError(), "no_active_transaction"),
        (RunAlreadyExistsError(RunId.new()), "run_already_exists"),
        (DecisionLogRewrittenError(RunId.new()), "decision_log_rewritten"),
        (IdempotencyKeyExistsError(RunId.new(), "idem-key-1"), "idempotency_key_exists"),
    ],
)
def test_port_errors_are_domain_errors_with_a_stable_code(error: DomainError, code: str) -> None:
    assert error.code == code
