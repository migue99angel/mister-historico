"""`RatingSheetStore` implementations against the shared contract suite."""

import shutil
from pathlib import Path

import pytest

from mister.catalog.application.ratings_tool import RatingSheetStore
from mister.catalog.infrastructure.content_schema.rating_sheets import YamlRatingSheetStore
from mister.catalog.infrastructure.in_memory.rating_sheets import InMemoryRatingSheetStore
from tests.contracts.suites.rating_sheet_store import CLUB_SEASON, RatingSheetStoreContract

FIXTURE_ROOT = Path(__file__).parent.parent / "fixtures" / "content"


class TestInMemoryRatingSheetStore(RatingSheetStoreContract):
    @pytest.fixture
    def store(self) -> RatingSheetStore:
        return InMemoryRatingSheetStore([YamlRatingSheetStore(FIXTURE_ROOT).load(CLUB_SEASON)])


class TestYamlRatingSheetStore(RatingSheetStoreContract):
    @pytest.fixture
    def store(self, tmp_path: Path) -> RatingSheetStore:
        shutil.copytree(FIXTURE_ROOT, tmp_path / "content")
        return YamlRatingSheetStore(tmp_path / "content")
