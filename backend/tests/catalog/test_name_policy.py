"""Real names may be hidden at presentation time."""

from mister.catalog.domain.name_policy import NamePolicy


def test_alias_is_used_when_real_names_are_disabled() -> None:
    assert NamePolicy(real_names=False).display("Real Name", "Alias") == "Alias"


def test_real_name_is_used_when_enabled() -> None:
    assert NamePolicy(real_names=True).display("Real Name", "Alias") == "Real Name"
