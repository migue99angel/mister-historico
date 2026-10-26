"""Real names may be hidden at presentation time."""

import pytest

from mister.catalog.domain.name_policy import NamePolicy
from mister.shared_kernel.errors import InvalidValueError


def test_alias_is_used_when_real_names_are_disabled() -> None:
    assert NamePolicy(real_names=False).display("Real Name", "Alias") == "Alias"


def test_real_name_is_used_when_enabled() -> None:
    assert NamePolicy(real_names=True).display("Real Name", "Alias") == "Real Name"


def test_name_policy_requires_an_explicit_boolean() -> None:
    with pytest.raises(InvalidValueError):
        NamePolicy(real_names=1)  # type: ignore[arg-type]
