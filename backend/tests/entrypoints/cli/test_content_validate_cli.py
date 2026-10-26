"""The public content validation command reports all issues and exit meanings."""

from pathlib import Path
from shutil import copytree

import pytest
from typer.testing import CliRunner

from mister.entrypoints.cli.app import app

CONTENT_ROOT = Path(__file__).resolve().parents[2] / "fixtures" / "content"
runner = CliRunner()


@pytest.fixture
def root(tmp_path: Path) -> Path:
    destination = tmp_path / "content"
    copytree(CONTENT_ROOT, destination)
    return destination


def test_valid_synthetic_tree_reports_one_playable_season(root: Path) -> None:
    result = runner.invoke(app, ["content", "validate", "--root", str(root), "--release"])

    assert result.exit_code == 0, result.output
    assert "1 temporada jugable" in result.output


def test_empty_root_is_valid_but_not_described_as_playable(tmp_path: Path) -> None:
    result = runner.invoke(app, ["content", "validate", "--root", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert "0 temporadas jugables" in result.output
    assert "catálogo vacío" in result.output


def test_draft_text_only_fails_release_validation(root: Path) -> None:
    path = root / "seasons" / "test-fc-2000-01" / "texts.yaml"
    path.write_text(path.read_text().replace("status: reviewed", "status: draft", 1))

    normal = runner.invoke(app, ["content", "validate", "--root", str(root)])
    release = runner.invoke(app, ["content", "validate", "--root", str(root), "--release"])

    assert normal.exit_code == 0, normal.output
    assert release.exit_code == 1
    assert "texts.yaml" in release.output


def test_all_content_issues_are_printed_and_fail_with_code_one(root: Path) -> None:
    fixtures = root / "seasons" / "test-fc-2000-01" / "fixtures.yaml"
    texts = root / "seasons" / "test-fc-2000-01" / "texts.yaml"
    fixtures.write_text(fixtures.read_text() + "\nunexpected: true\n")
    texts.write_text(texts.read_text() + "\nunexpected: true\n")

    result = runner.invoke(app, ["content", "validate", "--root", str(root)])

    assert result.exit_code == 1
    assert "fixtures.yaml" in result.output
    assert "texts.yaml" in result.output
    assert "temporadas jugables" not in result.output


def test_unavailable_root_fails_with_code_two(tmp_path: Path) -> None:
    result = runner.invoke(app, ["content", "validate", "--root", str(tmp_path / "missing")])

    assert result.exit_code == 2
    assert "missing" in result.output
