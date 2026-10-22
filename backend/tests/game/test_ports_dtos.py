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
    RunAlreadyExistsError,
    RunNotFoundError,
)
from mister.shared_kernel.errors import DomainError, InvalidValueError
from mister.shared_kernel.ids import RunId


def test_a_run_record_is_immutable() -> None:
    record = make_run_record()

    with pytest.raises(FrozenInstanceError):
        record.version = 2  # type: ignore[misc]


def test_a_run_starts_at_version_one_or_later() -> None:
    with pytest.raises(InvalidValueError, match="version"):
        replace(make_run_record(), version=0)


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


def test_idempotency_needs_a_key_and_a_request_hash() -> None:
    record = make_idempotency_record(make_run_record())

    with pytest.raises(InvalidValueError, match="key"):
        replace(record, key="")
    with pytest.raises(InvalidValueError, match="key"):
        replace(record, key="k" * 256)
    with pytest.raises(InvalidValueError, match="request_hash"):
        replace(record, request_hash="")


def test_the_idempotent_response_must_be_json_serializable_and_timestamped() -> None:
    record = make_idempotency_record(make_run_record())

    with pytest.raises(InvalidValueError, match="JSON"):
        replace(record, response={"when": T0})
    with pytest.raises(InvalidValueError, match="timezone"):
        replace(record, created_at=datetime(2026, 10, 22))


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (ConcurrencyError(RunId.new(), expected=1), "version_conflict"),
        (RunNotFoundError(RunId.new()), "run_not_found"),
        (RunAlreadyExistsError(RunId.new()), "run_already_exists"),
        (DecisionLogRewrittenError(RunId.new()), "decision_log_rewritten"),
        (IdempotencyKeyExistsError(RunId.new(), "key-1"), "idempotency_key_exists"),
    ],
)
def test_port_errors_are_domain_errors_with_a_stable_code(error: DomainError, code: str) -> None:
    assert error.code == code
