"""`Seed`: an unsigned 64-bit integer."""

from dataclasses import FrozenInstanceError

import pytest
from hypothesis import given
from hypothesis import strategies as st

from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.seed import Seed

MAX = 2**64 - 1


@given(value=st.integers(min_value=0, max_value=MAX))
def test_seed_accepts_any_unsigned_64_bit_integer(value: int) -> None:
    assert Seed(value).value == value
    assert int(Seed(value)) == value


@pytest.mark.parametrize("value", [-1, MAX + 1, 2**100])
def test_seed_rejects_out_of_range_values(value: int) -> None:
    with pytest.raises(InvalidValueError):
        Seed(value)


@pytest.mark.parametrize("value", [1.5, "7", None, True])
def test_seed_rejects_non_integers(value: object) -> None:
    with pytest.raises(InvalidValueError):
        Seed(value)  # type: ignore[arg-type]


def test_seed_is_immutable_and_comparable() -> None:
    seed = Seed(7)

    with pytest.raises(FrozenInstanceError):
        seed.value = 8  # type: ignore[misc]
    assert Seed(7) == seed
    assert Seed(8) != seed
