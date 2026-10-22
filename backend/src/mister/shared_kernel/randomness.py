"""Deterministic randomness with derived streams (ADR-005).

`RandomSource` is the only way the domain gets randomness. A source is identified by a `Seed`
plus a path of keys; `stream(*keys)` derives an independent child source, so e.g. every match
uses `root.stream("match", fixture_id)` and a decision that changes one match never shifts the
randomness of another.

Implementation notes (`StdlibRandomSource`):

- Each stream owns a `random.Random(int_seed)`, where `int_seed` is a BLAKE2b hash of the
  seed and the unambiguously serialised key path (see `_derive_int_seed`).
- Only `Random.random()` is used. It is the one method whose output sequence Python guarantees
  across versions; `randrange`, `choice`, `gauss`... are explicitly allowed to change. Every
  distribution here is implemented on top of `random()`, one draw at a time.
- numpy is deliberately not used: its distributions are not stable across versions, which
  would break golden tests and replays.
"""

import hashlib
import math
import random
from bisect import bisect_right
from collections.abc import Sequence
from itertools import accumulate
from typing import Protocol, Self, TypeVar

from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.seed import Seed

T = TypeVar("T")

type Key = str | int

#: Upper bound of the accepted `lam` in `poisson`: `exp(-lam)` must stay a normal float and
#: the inverse-transform search is linear in `lam`. Football goal rates are far below it.
POISSON_MAX_LAMBDA = 500.0


class RandomSource(Protocol):
    """Port for deterministic randomness. Same seed and same keys give the same values."""

    def stream(self, *keys: Key) -> Self:
        """Derive an independent child source for `keys` (at least one); this one is untouched."""
        ...

    def random(self) -> float:
        """Uniform float in [0, 1)."""
        ...

    def poisson(self, lam: float) -> int:
        """Poisson-distributed integer with mean `lam` (0 < lam <= 500). Consumes one draw."""
        ...

    def choice(self, seq: Sequence[T]) -> T:
        """Uniformly pick one element of a non-empty sequence. Consumes one draw."""
        ...

    def uniform(self, a: float, b: float) -> float:
        """Uniform float in [a, b] (finite bounds, a <= b). Consumes one draw."""
        ...

    def weighted_choice(self, items: Sequence[T], weights: Sequence[float]) -> T:
        """Pick an item with probability proportional to its weight. Consumes one draw."""
        ...


def _serialise_key(key: Key) -> bytes:
    """Encode a key as `<type tag><8-byte length><payload>`, so concatenations never collide."""
    if isinstance(key, bool) or not isinstance(key, str | int):
        raise InvalidValueError(f"stream keys must be str or int, got {type(key).__name__}")
    if isinstance(key, str):
        tag, payload = b"s", key.encode("utf-8")
    else:
        tag, payload = b"i", str(key).encode("ascii")
    return tag + len(payload).to_bytes(8, "big") + payload


def _derive_int_seed(seed: Seed, keys: Sequence[Key]) -> int:
    """Stable 64-bit integer seed for `Random`, from the seed and the key path."""
    hasher = hashlib.blake2b(digest_size=8)
    hasher.update(seed.value.to_bytes(8, "big"))
    for key in keys:
        hasher.update(_serialise_key(key))
    return int.from_bytes(hasher.digest(), "big")


class StdlibRandomSource:
    """`RandomSource` in pure Python on top of `random.Random(int).random()`."""

    def __init__(self, seed: Seed, _keys: tuple[Key, ...] = ()) -> None:
        self._seed = seed
        self._keys = _keys
        self._rng = random.Random(_derive_int_seed(seed, _keys))  # noqa: S311 - not crypto

    def stream(self, *keys: Key) -> Self:
        """Derive `stream(*keys)`. Nesting composes: `s.stream("a").stream("b")` equals
        `s.stream("a", "b")`. The parent state is not touched."""
        if len(keys) == 0:
            raise InvalidValueError("stream needs at least one key")
        return type(self)(self._seed, (*self._keys, *keys))

    def random(self) -> float:
        return self._rng.random()

    def poisson(self, lam: float) -> int:
        """Inverse-transform sampling: one uniform draw `u`, then the smallest `k` with
        `P(X <= k) >= u`, accumulating the pmf with `p(k) = p(k-1) * lam / k`.

        Valid for `0 < lam <= POISSON_MAX_LAMBDA`; expected cost is O(lam). Using a single
        draw per call keeps the number of draws consumed independent of the outcome.

        The search stops at `k_max = ceil(lam + 12 * sqrt(lam) + 20)`. Without the cut, a
        draw above the largest representable cdf (rounding leaves it just below 1) would
        walk far into the tail. The cut biases only outcomes beyond 12 standard deviations,
        whose probability is below 1e-30: negligible.
        """
        if not math.isfinite(lam) or not 0.0 < lam <= POISSON_MAX_LAMBDA:
            raise InvalidValueError(
                f"poisson lambda must be finite and in (0, {POISSON_MAX_LAMBDA}], got {lam}"
            )
        u = self.random()
        k = 0
        p = math.exp(-lam)
        cdf = p
        k_max = math.ceil(lam + 12 * math.sqrt(lam) + 20)
        while u > cdf and k < k_max:
            k += 1
            p *= lam / k
            cdf += p
        return k

    def choice(self, seq: Sequence[T]) -> T:
        if len(seq) == 0:
            raise InvalidValueError("cannot choose from an empty sequence")
        return seq[int(self.random() * len(seq))]

    def uniform(self, a: float, b: float) -> float:
        if not (math.isfinite(a) and math.isfinite(b) and a <= b):
            raise InvalidValueError(f"uniform needs finite bounds with a <= b, got ({a}, {b})")
        return min(a + (b - a) * self.random(), b)

    def weighted_choice(self, items: Sequence[T], weights: Sequence[float]) -> T:
        if len(items) == 0 or len(items) != len(weights):
            raise InvalidValueError("items and weights must be non-empty and of equal length")
        if not all(math.isfinite(w) and w >= 0.0 for w in weights):
            raise InvalidValueError("weights must be finite and non-negative")
        cumulative = list(accumulate(weights))
        total = cumulative[-1]
        if total <= 0.0:
            raise InvalidValueError("at least one weight must be positive")
        last_positive = max(i for i, w in enumerate(weights) if w > 0.0)
        # First index whose cumulative weight exceeds r; zero-weight items are skipped because
        # they share their predecessor's cumulative value. The clamp covers float rounding.
        index = bisect_right(cumulative, self.random() * total)
        return items[min(index, last_positive)]
