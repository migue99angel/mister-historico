"""Deterministic run-token fake for tests."""

import hashlib
from itertools import count


class FakeRunTokenGenerator:
    """Deterministic tokens (a counter run through SHA-256, URL-safe, 43 characters)."""

    def __init__(self) -> None:
        self._counter = count(1)

    def generate(self) -> str:
        digest = hashlib.sha256(f"fake-run-token-{next(self._counter)}".encode()).hexdigest()
        return digest[:43].replace("a", "-").replace("b", "_")
