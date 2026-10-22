"""Contracts of the run-token ports: `RunTokenGenerator` and `RunTokenHasher`.

The run token is a bearer secret (OpenAPI): the server keeps only its hash.
"""

import re
from collections.abc import Callable

import pytest

from mister.game.application.ports import RunTokenGenerator, RunTokenHasher

GeneratorFactory = Callable[[], RunTokenGenerator]
HasherFactory = Callable[[], RunTokenHasher]

# 32 random bytes in unpadded URL-safe base64 are 43 characters.
MIN_TOKEN_LENGTH = 43
URL_SAFE = re.compile(r"[A-Za-z0-9_-]+")


class RunTokenGeneratorContract:
    @pytest.fixture
    def make_generator(self) -> GeneratorFactory:
        raise NotImplementedError

    def test_a_token_is_url_safe_and_carries_at_least_32_bytes(
        self, make_generator: GeneratorFactory
    ) -> None:
        token = make_generator().generate()

        assert URL_SAFE.fullmatch(token)
        assert len(token) >= MIN_TOKEN_LENGTH

    def test_tokens_do_not_repeat(self, make_generator: GeneratorFactory) -> None:
        generator = make_generator()

        tokens = {generator.generate() for _ in range(50)}

        assert len(tokens) == 50


class RunTokenHasherContract:
    @pytest.fixture
    def make_hasher(self) -> HasherFactory:
        raise NotImplementedError

    def test_the_hash_is_not_the_token_and_does_not_contain_it(
        self, make_hasher: HasherFactory
    ) -> None:
        token = "s3cr3t-token-value"  # noqa: S105

        assert token not in make_hasher().hash(token)

    def test_the_same_token_always_gets_the_same_hash(self, make_hasher: HasherFactory) -> None:
        hasher = make_hasher()

        assert hasher.hash("token-a") == hasher.hash("token-a")

    def test_different_tokens_get_different_hashes(self, make_hasher: HasherFactory) -> None:
        hasher = make_hasher()

        assert hasher.hash("token-a") != hasher.hash("token-b")

    def test_verify_accepts_the_token_that_produced_the_hash(
        self, make_hasher: HasherFactory
    ) -> None:
        hasher = make_hasher()

        assert hasher.verify("token-a", hasher.hash("token-a"))

    def test_verify_rejects_any_other_token(self, make_hasher: HasherFactory) -> None:
        hasher = make_hasher()

        assert not hasher.verify("token-b", hasher.hash("token-a"))
        assert not hasher.verify("", hasher.hash("token-a"))
