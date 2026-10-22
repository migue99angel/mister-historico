"""`Seed`: the value that fixes all the randomness of a run (ADR-005)."""

from dataclasses import dataclass

from mister.shared_kernel.errors import InvalidValueError

SEED_BITS = 64
SEED_MAX = 2**SEED_BITS - 1


@dataclass(frozen=True, slots=True)
class Seed:
    """An unsigned 64-bit integer."""

    value: int

    def __post_init__(self) -> None:
        # bool is an int subclass, but `Seed(True)` is certainly a bug.
        if not isinstance(self.value, int) or isinstance(self.value, bool):
            raise InvalidValueError(f"Seed must be an integer, got {type(self.value).__name__}")
        if not 0 <= self.value <= SEED_MAX:
            raise InvalidValueError(f"Seed must be in [0, 2**64), got {self.value}")

    def __int__(self) -> int:
        return self.value
