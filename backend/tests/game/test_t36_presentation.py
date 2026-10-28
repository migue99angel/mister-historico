"""Public Game presentation never exposes private domain or catalog data."""

from mister.catalog.application.api import present_person_name


def test_published_name_helper_uses_alias_when_real_names_are_disabled() -> None:
    assert present_person_name("Real Person", "Alias Person", real_names=False) == "Alias Person"
