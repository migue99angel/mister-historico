"""Real loader diagnostics retain POSIX filenames when translated to application issues."""

from pathlib import Path

import pytest

from mister.catalog.application.validation_types import ContentValidationReport, ValidationIssue
from mister.catalog.infrastructure.content_schema import ContentValidationError, load_content_tree


def test_a_malformed_file_with_a_literal_backslash_keeps_the_loader_diagnostic(
    tmp_path: Path,
) -> None:
    clubs = tmp_path / "clubs"
    clubs.mkdir()
    path = clubs / r"bad\name.yaml"
    path.write_text("not: [valid YAML", encoding="utf-8")

    with pytest.raises(ContentValidationError) as caught:
        load_content_tree(tmp_path, release=False)
    assert len(caught.value.issues) == 1
    original = caught.value.issues[0]
    assert original.path == r"clubs/bad\name.yaml"

    translated = ValidationIssue(original.path, original.field, original.message)
    report = ContentValidationReport((translated,), None)

    assert (translated.path, translated.field, translated.message) == (
        original.path,
        original.field,
        original.message,
    )
    assert report.issues[0].path == r"clubs/bad\name.yaml"
    assert not report.valid
    assert report.season_count is None
