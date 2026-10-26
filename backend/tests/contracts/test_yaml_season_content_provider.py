"""The YAML provider must satisfy the published season content contract."""

from pathlib import Path
from shutil import copytree

import pytest

from mister.catalog.application.api import SeasonContentProvider
from mister.catalog.infrastructure.content_schema import ContentValidationError
from mister.catalog.infrastructure.yaml_season_content import YamlSeasonContentProvider
from mister.shared_kernel.errors import InvalidValueError
from tests.contracts.suites.season_content_provider import SeasonContentProviderContract

CONTENT_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "content"


class TestYamlSeasonContentProvider(SeasonContentProviderContract):
    @pytest.fixture
    def provider(self) -> SeasonContentProvider:
        return YamlSeasonContentProvider(CONTENT_ROOT)


def test_empty_content_tree_lists_no_seasons(tmp_path: Path) -> None:
    assert YamlSeasonContentProvider(tmp_path).list_playable_seasons() == ()


def test_missing_content_directory_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(InvalidValueError, match="content root"):
        YamlSeasonContentProvider(tmp_path / "missing").list_playable_seasons()


def test_draft_text_cannot_be_published(tmp_path: Path) -> None:
    root = tmp_path / "content"
    copytree(CONTENT_ROOT, root)
    path = root / "seasons" / "test-fc-2000-01" / "texts.yaml"
    path.write_text(path.read_text().replace("status: reviewed", "status: draft", 1))

    with pytest.raises(ContentValidationError):
        YamlSeasonContentProvider(root).list_playable_seasons()
