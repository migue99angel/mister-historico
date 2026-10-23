"""`RatingSheetStore` implementations against the shared contract suite."""

import shutil
from pathlib import Path

import pytest

from mister.catalog.application.ports import RatingSheetStore
from mister.catalog.infrastructure.content_schema.rating_sheets import YamlRatingSheetStore
from mister.catalog.infrastructure.in_memory.rating_sheets import InMemoryRatingSheetStore
from tests.contracts.suites.rating_sheet_store import CLUB_SEASON, RatingSheetStoreContract

FIXTURE_ROOT = Path(__file__).parent.parent / "fixtures" / "content"


class TestInMemoryRatingSheetStore(RatingSheetStoreContract):
    @pytest.fixture
    def store(self) -> RatingSheetStore:
        yaml_store = YamlRatingSheetStore(FIXTURE_ROOT)
        return InMemoryRatingSheetStore(
            [yaml_store.load(CLUB_SEASON), yaml_store.load("_market-2000-01")]
        )


class TestYamlRatingSheetStore(RatingSheetStoreContract):
    @pytest.fixture
    def store(self, tmp_path: Path) -> RatingSheetStore:
        shutil.copytree(FIXTURE_ROOT, tmp_path / "content")
        return YamlRatingSheetStore(tmp_path / "content")
