"""Run-token adapters used in production.

The token is 32 random bytes, so hashing it with an unsalted SHA-256 is enough: there is no
low-entropy secret to brute-force, unlike a human password.
"""

import hashlib
import hmac
import secrets

TOKEN_BYTES = 32


class SecretsRunTokenGenerator:
    """Random URL-safe tokens of 32 bytes (43 characters), from `secrets`."""

    def generate(self) -> str:
        return secrets.token_urlsafe(TOKEN_BYTES)


class Sha256RunTokenHasher:
    """Hex SHA-256 of the token, compared in constant time."""

    def hash(self, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def verify(self, token: str, token_hash: str) -> bool:
        return hmac.compare_digest(self.hash(token), token_hash)
