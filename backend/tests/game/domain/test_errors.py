import pytest

from mister.game.domain.errors import (
    AlreadyDecidedError,
    InvalidDecisionError,
    InvalidRunTransitionError,
)
from mister.shared_kernel.errors import DomainError


@pytest.mark.parametrize(
    "error_type,code",
    [
        (AlreadyDecidedError, "already_decided"),
        (InvalidDecisionError, "invalid_decision"),
        (InvalidRunTransitionError, "invalid_run_transition"),
    ],
)
def test_run_errors_are_domain_errors_with_stable_codes(error_type: type[DomainError], code: str) -> None:
    error = error_type("rule violated")

    assert isinstance(error, DomainError)
    assert error.code == code
