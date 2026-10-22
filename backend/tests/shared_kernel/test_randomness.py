"""`RandomSource` / `StdlibRandomSource` (ADR-005): determinism, derived streams, distributions."""

import math
from collections import Counter

import pytest
from hypothesis import given
from hypothesis import strategies as st

from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.randomness import RandomSource, StdlibRandomSource
from mister.shared_kernel.seed import Seed

seeds = st.integers(min_value=0, max_value=2**64 - 1).map(Seed)
keys = st.one_of(st.text(max_size=8), st.integers(min_value=-(2**70), max_value=2**70))
key_paths = st.lists(keys, max_size=4)


def draw(source: RandomSource, n: int = 8) -> list[float]:
    return [source.random() for _ in range(n)]


# ----------------------------------------------------------------------- determinism


@given(seed=seeds, path=key_paths)
def test_same_seed_and_same_keys_give_the_same_sequence(seed: Seed, path: list[str | int]) -> None:
    first = StdlibRandomSource(seed).stream(*path)
    second = StdlibRandomSource(seed).stream(*path)

    assert draw(first) == draw(second)


@given(seed=seeds)
def test_different_seeds_give_different_sequences(seed: Seed) -> None:
    other = Seed((seed.value + 1) % 2**64)

    assert draw(StdlibRandomSource(seed)) != draw(StdlibRandomSource(other))


def test_different_keys_give_different_streams() -> None:
    root = StdlibRandomSource(Seed(42))

    assert draw(root.stream("match", "fx-1")) != draw(root.stream("match", "fx-2"))
    assert draw(root.stream("a")) != draw(root)


def test_keys_are_not_ambiguous_across_concatenation() -> None:
    root = StdlibRandomSource(Seed(42))

    assert draw(root.stream("a", "bc")) != draw(root.stream("ab", "c"))
    assert draw(root.stream("a", "")) != draw(root.stream("", "a"))
    assert draw(root.stream("ab")) != draw(root.stream("a", "b"))


def test_integer_keys_differ_from_their_string_form() -> None:
    root = StdlibRandomSource(Seed(42))

    assert draw(root.stream(1)) != draw(root.stream("1"))
    assert draw(root.stream(1)) != draw(root.stream(-1))


def test_a_nested_stream_equals_the_stream_with_the_joined_keys() -> None:
    root = StdlibRandomSource(Seed(42))

    assert draw(root.stream("a").stream("b")) == draw(root.stream("a", "b"))


@pytest.mark.parametrize("bad_key", [1.5, None, True, b"x"])
def test_stream_rejects_keys_that_are_not_str_or_int(bad_key: object) -> None:
    with pytest.raises(InvalidValueError):
        StdlibRandomSource(Seed(1)).stream(bad_key)  # type: ignore[arg-type]


# ----------------------------------------------------------------------- independence


def test_deriving_a_stream_does_not_consume_the_parent() -> None:
    untouched = StdlibRandomSource(Seed(7))
    parent = StdlibRandomSource(Seed(7))

    draw(parent.stream("match", 1))
    draw(parent.stream("match", 2))

    assert draw(parent) == draw(untouched)


def test_consuming_a_stream_does_not_alter_the_parent_or_a_sibling() -> None:
    reference = StdlibRandomSource(Seed(7))
    expected_parent = draw(reference)
    expected_sibling = draw(reference.stream("b"))

    root = StdlibRandomSource(Seed(7))
    child = root.stream("a")
    sibling = root.stream("b")
    draw(child, 1000)

    assert draw(sibling) == expected_sibling
    assert draw(root) == expected_parent


def test_deriving_the_same_stream_twice_restarts_it() -> None:
    root = StdlibRandomSource(Seed(7))

    assert draw(root.stream("a")) == draw(root.stream("a"))


def test_stream_without_keys_is_rejected() -> None:
    with pytest.raises(InvalidValueError):
        StdlibRandomSource(Seed(1)).stream()


# ----------------------------------------------------------------------- unit interval


@given(seed=seeds)
def test_random_is_in_the_half_open_unit_interval(seed: Seed) -> None:
    assert all(0.0 <= value < 1.0 for value in draw(StdlibRandomSource(seed), 50))


# ----------------------------------------------------------------------- poisson


@pytest.mark.parametrize("lam", [0.2, 0.5, 1.0, 1.5, 2.5, 4.0])
def test_poisson_mean_and_variance_converge_to_lambda(lam: float) -> None:
    n = 20_000
    source = StdlibRandomSource(Seed(2024)).stream("poisson", str(lam))

    samples = [source.poisson(lam) for _ in range(n)]

    mean = sum(samples) / n
    variance = sum((s - mean) ** 2 for s in samples) / (n - 1)
    # Five standard errors: deterministic (seeded) and far from flaky.
    assert abs(mean - lam) < 5 * math.sqrt(lam / n)
    assert abs(variance - lam) < 5 * math.sqrt((lam + 2 * lam**2) / n)


def test_poisson_returns_non_negative_integers() -> None:
    source = StdlibRandomSource(Seed(3))

    samples = [source.poisson(2.0) for _ in range(200)]

    assert all(isinstance(s, int) and s >= 0 for s in samples)


def test_poisson_consumes_exactly_one_random_draw() -> None:
    a = StdlibRandomSource(Seed(5))
    b = StdlibRandomSource(Seed(5))

    a.poisson(3.0)
    b.random()

    assert a.random() == b.random()


@pytest.mark.parametrize("lam", [0.0, -1.0, math.nan, math.inf, -math.inf, 1e6])
def test_poisson_rejects_invalid_lambda(lam: float) -> None:
    with pytest.raises(InvalidValueError):
        StdlibRandomSource(Seed(1)).poisson(lam)


@pytest.mark.parametrize("lam", [50.0, 500.0])
def test_poisson_mean_and_variance_converge_for_large_lambda(lam: float) -> None:
    n = 4_000
    source = StdlibRandomSource(Seed(2025)).stream("poisson-large", str(lam))

    samples = [source.poisson(lam) for _ in range(n)]

    mean = sum(samples) / n
    variance = sum((s - mean) ** 2 for s in samples) / (n - 1)
    assert abs(mean - lam) < 5 * math.sqrt(lam / n)
    assert abs(variance - lam) < 5 * math.sqrt((lam + 2 * lam**2) / n)


@pytest.mark.parametrize("lam", [0.2, 1.5, 50.0, 500.0])
def test_poisson_tail_is_cut_at_a_reasonable_maximum(lam: float) -> None:
    class Almost1(StdlibRandomSource):
        def random(self) -> float:
            return 1.0 - 2**-53

    value = Almost1(Seed(1)).poisson(lam)

    k_max = math.ceil(lam + 12 * math.sqrt(lam) + 20)
    assert value <= k_max


# ----------------------------------------------------------------------- choice / uniform


def test_choice_picks_every_element_roughly_uniformly() -> None:
    source = StdlibRandomSource(Seed(11))

    counts = Counter(source.choice(["a", "b", "c", "d"]) for _ in range(8000))

    assert set(counts) == {"a", "b", "c", "d"}
    assert all(abs(c - 2000) < 5 * math.sqrt(8000 * 0.25 * 0.75) for c in counts.values())


def test_choice_works_on_tuples_and_strings() -> None:
    source = StdlibRandomSource(Seed(11))

    assert source.choice((7,)) == 7
    assert source.choice("z") == "z"


def test_choice_rejects_an_empty_sequence() -> None:
    with pytest.raises(InvalidValueError):
        StdlibRandomSource(Seed(1)).choice([])


@given(seed=seeds, a=st.floats(-1e6, 1e6), width=st.floats(0.001, 1e6))
def test_uniform_stays_within_its_bounds(seed: Seed, a: float, width: float) -> None:
    value = StdlibRandomSource(seed).uniform(a, a + width)

    assert a <= value <= a + width


def test_uniform_rejects_non_finite_or_inverted_bounds() -> None:
    source = StdlibRandomSource(Seed(1))

    with pytest.raises(InvalidValueError):
        source.uniform(2.0, 1.0)
    with pytest.raises(InvalidValueError):
        source.uniform(0.0, math.inf)
    with pytest.raises(InvalidValueError):
        source.uniform(math.nan, 1.0)


# ----------------------------------------------------------------------- weighted_choice


def test_weighted_choice_respects_the_weights() -> None:
    source = StdlibRandomSource(Seed(99))
    n = 20_000

    counts = Counter(source.weighted_choice(["a", "b", "c"], [1.0, 2.0, 7.0]) for _ in range(n))

    for item, share in [("a", 0.1), ("b", 0.2), ("c", 0.7)]:
        assert abs(counts[item] / n - share) < 5 * math.sqrt(share * (1 - share) / n)


def test_weighted_choice_never_picks_zero_weight_items() -> None:
    source = StdlibRandomSource(Seed(99))

    picks = {source.weighted_choice(["x", "y", "z"], [0.0, 1.0, 0.0]) for _ in range(500)}

    assert picks == {"y"}


def test_weighted_choice_never_picks_a_trailing_zero_weight_item_on_rounding() -> None:
    class Almost1(StdlibRandomSource):
        def random(self) -> float:
            return 1.0 - 2**-53

    assert Almost1(Seed(1)).weighted_choice(["x", "y"], [0.1, 0.0]) == "x"


@pytest.mark.parametrize(
    ("items", "weights"),
    [
        ([], []),
        (["a", "b"], [1.0]),
        (["a"], [-1.0]),
        (["a", "b"], [0.0, 0.0]),
        (["a"], [math.nan]),
        (["a"], [math.inf]),
    ],
)
def test_weighted_choice_rejects_invalid_weights(items: list[str], weights: list[float]) -> None:
    with pytest.raises(InvalidValueError):
        StdlibRandomSource(Seed(1)).weighted_choice(items, weights)


# ----------------------------------------------------------------------- protocol


def test_stdlib_random_source_satisfies_the_protocol() -> None:
    source: RandomSource = StdlibRandomSource(Seed(1))  # mypy checks structural compatibility

    assert isinstance(source.stream("x"), StdlibRandomSource)


# ----------------------------------------------------------------------- golden values


def test_golden_random_values_never_change() -> None:
    """Pins the exact sequence. If this fails, every replay and golden test is invalidated."""
    source = StdlibRandomSource(Seed(20121213)).stream("golden")

    assert draw(source, 5) == [
        0.6095593629330438,
        0.03260291500339596,
        0.5360276883429727,
        0.17276581438283778,
        0.27663068755713804,
    ]


def test_golden_poisson_values_never_change() -> None:
    source = StdlibRandomSource(Seed(20121213)).stream("golden")

    assert [source.poisson(1.5) for _ in range(5)] == [2, 0, 1, 0, 1]


@pytest.mark.parametrize(
    ("lam", "expected"),
    [
        (
            0.3,
            [0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 1]
            + [0, 0],
        ),
        (3.0, [3, 0, 3, 1, 2, 2, 1, 3]),
    ],
)
def test_golden_poisson_values_for_other_lambdas_never_change(
    lam: float, expected: list[int]
) -> None:
    source = StdlibRandomSource(Seed(20121213)).stream("golden")

    assert [source.poisson(lam) for _ in range(len(expected))] == expected
