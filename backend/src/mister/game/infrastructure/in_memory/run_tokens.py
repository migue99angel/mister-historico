"""Run-token adapters that need no external service.

`Sha256RunTokenHasher` is also what production can use: the token is 32 random bytes, so an
unsalted SHA-256 is enough (there is no low-entropy secret to brute-force).
"""

import hashlib
import hmac
from itertools import count


class FakeRunTokenGenerator:
    """Deterministic tokens (a counter run through SHA-256, base64url-style, 43 characters)."""

    def __init__(self) -> None:
        self._counter = count(1)

    def generate(self) -> str:
        digest = hashlib.sha256(f"fake-run-token-{next(self._counter)}".encode()).hexdigest()
        return digest[:43].replace("a", "-").replace("b", "_")


class Sha256RunTokenHasher:
    """Hex SHA-256 of the token, compared in constant time."""

    def hash(self, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def verify(self, token: str, token_hash: str) -> bool:
        return hmac.compare_digest(self.hash(token), token_hash)
