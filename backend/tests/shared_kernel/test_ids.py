"""Typed identifiers: validation, immutability and type safety."""

from dataclasses import FrozenInstanceError
from typing import Any
from uuid import UUID, uuid4

import pytest
from hypothesis import given
from hypothesis import strategies as st

from mister.shared_kernel.errors import DomainError, InvalidValueError
from mister.shared_kernel.ids import (
    BlockId,
    ClubId,
    ClubSeasonId,
    CompetitionId,
    DilemmaId,
    FixtureId,
    OptionId,
    PlayableSeasonId,
    PlayerId,
    RunId,
)

SLUG_IDS = [
    BlockId,
    ClubSeasonId,
    PlayableSeasonId,
    PlayerId,
    ClubId,
    CompetitionId,
    FixtureId,
    DilemmaId,
    OptionId,
]

valid_slugs = st.from_regex(r"[a-z0-9]+(-[a-z0-9]+)*", fullmatch=True).filter(
    lambda s: len(s) <= 64
)
NON_MARKET_IDS = [i for i in SLUG_IDS if i is not ClubSeasonId]


@pytest.mark.parametrize("id_type", SLUG_IDS)
@pytest.mark.parametrize("slug", ["real-madrid-2012-13", "a", "test-fc-2000-01", "x1-y2", "a" * 64])
def test_slug_ids_accept_kebab_case_slugs(id_type: Any, slug: str) -> None:
    identifier = id_type(slug)

    assert identifier.value == slug
    assert str(identifier) == slug


@given(slug=valid_slugs)
def test_any_kebab_case_slug_is_accepted(slug: str) -> None:
    assert PlayerId(slug).value == slug


@pytest.mark.parametrize("id_type", SLUG_IDS)
@pytest.mark.parametrize(
    "slug",
    [
        "",
        "Real-Madrid",
        "real madrid",
        "real_madrid",
        "-leading",
        "trailing-",
        "double--dash",
        "__double",
        "tilde-á",
        "a" * 65,
    ],
)
def test_slug_ids_reject_invalid_formats(id_type: Any, slug: str) -> None:
    with pytest.raises(InvalidValueError):
        id_type(slug)


def test_club_season_id_accepts_a_leading_underscore_for_system_slugs() -> None:
    assert ClubSeasonId("_market-2012-13").value == "_market-2012-13"


@pytest.mark.parametrize(
    "slug", ["__market", "_", "_-a", "_Market", "_foo-2000-01", "_market", "_market-"]
)
def test_club_season_id_rejects_malformed_underscore_slugs(slug: str) -> None:
    with pytest.raises(InvalidValueError):
        ClubSeasonId(slug)


@pytest.mark.parametrize("id_type", NON_MARKET_IDS)
def test_only_club_season_id_allows_a_leading_underscore(id_type: Any) -> None:
    with pytest.raises(InvalidValueError):
        id_type("_market-2012-13")


@pytest.mark.parametrize("id_type", SLUG_IDS)
def test_slug_ids_reject_non_string_values(id_type: Any) -> None:
    with pytest.raises(InvalidValueError):
        id_type(42)


def test_invalid_id_error_is_a_domain_error_with_a_stable_code() -> None:
    with pytest.raises(DomainError) as excinfo:
        PlayerId("Not A Slug")

    assert excinfo.value.code == "invalid_value"


def test_ids_are_immutable() -> None:
    player = PlayerId("bale")

    with pytest.raises(FrozenInstanceError):
        player.value = "other"  # type: ignore[misc]


def test_ids_of_the_same_type_and_value_are_equal_and_hashable() -> None:
    assert PlayerId("bale") == PlayerId("bale")
    assert len({PlayerId("bale"), PlayerId("bale"), PlayerId("modric")}) == 2


def test_ids_of_different_types_are_never_equal_at_runtime() -> None:
    assert PlayerId("same") != ClubId("same")  # type: ignore[comparison-overlap]
    assert len({PlayerId("same"), ClubId("same")}) == 2


def test_ids_of_different_types_are_not_interchangeable_for_mypy() -> None:
    def takes_player(player_id: PlayerId) -> PlayerId:
        return player_id

    # mypy --strict verifies the ignore below: if it ever stops being an error (the IDs
    # became interchangeable), `warn_unused_ignores` fails the type check.
    takes_player(ClubId("real-madrid"))  # type: ignore[arg-type]


def test_run_id_wraps_a_uuid() -> None:
    raw = uuid4()

    run_id = RunId(raw)

    assert run_id.value == raw
    assert str(run_id) == str(raw)


def test_run_id_new_generates_distinct_ids() -> None:
    assert RunId.new() != RunId.new()


def test_run_id_parses_its_string_form() -> None:
    run_id = RunId.new()

    assert RunId.parse(str(run_id)) == run_id


@pytest.mark.parametrize(
    "text",
    [
        "",
        "not-a-uuid",
        "1234",
        "urn:uuid:12345678-1234-5678-1234-567812345678",
        "12345678123456781234567812345678",
        "12345678-1234-5678-1234-56781234567A",
        "{12345678-1234-5678-1234-567812345678}",
    ],
)
def test_run_id_parse_rejects_malformed_text(text: str) -> None:
    with pytest.raises(InvalidValueError):
        RunId.parse(text)


def test_run_id_rejects_values_that_are_not_uuids() -> None:
    with pytest.raises(InvalidValueError):
        RunId("12345678-1234-5678-1234-567812345678")  # type: ignore[arg-type]


def test_run_id_is_not_a_slug_id() -> None:
    assert RunId(UUID(int=1)) != PlayerId("bale")  # type: ignore[comparison-overlap]
