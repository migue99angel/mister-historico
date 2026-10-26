"""YAML content diagnostics cross the application boundary without losing information."""

import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from tests.catalog.test_content_tree import edit

from mister.catalog.application.validation_types import (
    ContentValidationReport,
    ContentValidationUnavailableError,
    ValidationIssue,
)
from mister.catalog.infrastructure.content_schema import ContentValidationError, load_content_tree
from mister.catalog.infrastructure.yaml_validation import YamlContentValidator
from mister.shared_kernel.errors import InvalidValueError

_FIXTURE_ROOT = Path(__file__).parent.parent / "fixtures" / "content"
_SEASON = "seasons/test-fc-2000-01"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    target = tmp_path / "content"
    shutil.copytree(_FIXTURE_ROOT, target)
    return target


def test_all_loader_diagnostics_cross_the_boundary_with_their_original_text(root: Path) -> None:
    edit(root, f"{_SEASON}/season.yaml", lambda data: data.update(unexpected=True))
    (root / _SEASON / "texts.yaml").write_text("not: [valid YAML", encoding="utf-8")
    with pytest.raises(ContentValidationError) as caught:
        load_content_tree(root, release=False)
    expected = ContentValidationReport(
        tuple(
            ValidationIssue(issue.path, issue.field, issue.message) for issue in caught.value.issues
        ),
        None,
    )

    report = YamlContentValidator(root).validate(release=False)

    assert report == expected
    assert len(report.issues) == 2
    assert all(isinstance(issue, ValidationIssue) for issue in report.issues)
    assert report.season_count is None
    assert any(issue.field == "" for issue in report.issues)


def test_a_missing_required_file_is_content_invalidity_in_an_available_tree(root: Path) -> None:
    (root / _SEASON / "texts.yaml").unlink()

    report = YamlContentValidator(root).validate(release=False)

    assert report.issues == (ValidationIssue(f"{_SEASON}/texts.yaml", "", "file is missing"),)
    assert not report.valid
    assert report.season_count is None


@pytest.mark.parametrize("release", [False, True])
def test_a_file_cannot_be_used_as_the_content_root(tmp_path: Path, release: bool) -> None:
    root = tmp_path / "content"
    root.write_text("not a directory", encoding="utf-8")

    with pytest.raises(ContentValidationUnavailableError):
        YamlContentValidator(root).validate(release=release)


def test_a_validator_reads_changes_since_its_previous_call(root: Path) -> None:
    validator = YamlContentValidator(root)
    assert validator.validate(release=False).valid
    edit(root, f"{_SEASON}/season.yaml", lambda data: data.update(unexpected=True))

    report = validator.validate(release=False)

    assert not report.valid
    assert report.issues[0].field == "unexpected"


def test_a_root_removed_after_construction_is_operationally_unavailable(tmp_path: Path) -> None:
    root = tmp_path / "content"
    root.mkdir()
    validator = YamlContentValidator(root)
    assert validator.validate(release=False) == ContentValidationReport((), 0)
    root.rmdir()

    with pytest.raises(ContentValidationUnavailableError):
        validator.validate(release=False)


def test_file_read_failures_raise_the_application_operational_error(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_read = Path.read_text
    blocked = root / "clubs" / "test-fc.yaml"

    def read(path: Path, *args: Any, **kwargs: Any) -> str:
        if path == blocked:
            raise PermissionError("test content cannot be read")
        return original_read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read)

    with pytest.raises(ContentValidationUnavailableError) as caught:
        YamlContentValidator(root).validate(release=False)

    assert caught.value.code == "content_validation_unavailable"
    assert isinstance(caught.value.__cause__, PermissionError)


def test_an_unreadable_root_is_not_reported_as_a_valid_empty_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "content"
    root.mkdir()
    original_iterdir = Path.iterdir

    def iterdir(path: Path) -> Iterator[Path]:
        if path == root:
            raise PermissionError("test root cannot be listed")
        return original_iterdir(path)

    monkeypatch.setattr(Path, "iterdir", iterdir)

    with pytest.raises(ContentValidationUnavailableError) as caught:
        YamlContentValidator(root).validate(release=False)

    assert isinstance(caught.value.__cause__, PermissionError)


def test_a_decoding_failure_cannot_escape_as_an_infrastructure_read_error(root: Path) -> None:
    (root / "clubs" / "test-fc.yaml").write_bytes(b"\xff\xfe")

    with pytest.raises(ContentValidationUnavailableError) as caught:
        YamlContentValidator(root).validate(release=False)

    assert isinstance(caught.value.__cause__, UnicodeDecodeError)


@pytest.mark.parametrize("release", [0, 1, None, "release"])
def test_the_adapter_requires_an_explicit_boolean_mode(tmp_path: Path, release: Any) -> None:
    with pytest.raises(InvalidValueError):
        YamlContentValidator(tmp_path).validate(release=release)
