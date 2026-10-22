"""Domain errors carry a stable machine-readable code."""

import pytest

from mister.shared_kernel.errors import DomainError, InvalidValueError


def test_domain_error_has_a_default_code_and_message() -> None:
    error = DomainError("something broke")

    assert error.code == "domain_error"
    assert str(error) == "something broke"


def test_subclasses_define_their_own_stable_code() -> None:
    class RunNotFoundError(DomainError):
        code = "run_not_found"

    with pytest.raises(DomainError) as excinfo:
        raise RunNotFoundError("no such run")

    assert excinfo.value.code == "run_not_found"


def test_invalid_value_error_is_also_a_value_error() -> None:
    error = InvalidValueError("bad")

    assert isinstance(error, DomainError)
    assert isinstance(error, ValueError)
    assert error.code == "invalid_value"
