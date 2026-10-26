"""The YAML adapter runs the unchanged content-validation contract on Test FC trees."""

import shutil
from pathlib import Path

import pytest

from mister.catalog.application.ports import ContentValidator
from mister.catalog.infrastructure.yaml_validation import YamlContentValidator
from tests.catalog.test_content_tree import edit
from tests.contracts.suites.content_validator import (
    ContentValidatorContract,
    ValidationScenario,
    ValidatorFactory,
)

_FIXTURE_ROOT = Path(__file__).parent.parent / "fixtures" / "content"
_SEASON = "seasons/test-fc-2000-01"


class TestYamlContentValidator(ContentValidatorContract):
    @pytest.fixture
    def make_validator(self, tmp_path: Path) -> ValidatorFactory:
        def make(scenario: ValidationScenario) -> ContentValidator:
            root = tmp_path / scenario
            if scenario == "unavailable":
                return YamlContentValidator(root)
            if scenario == "empty":
                root.mkdir(exist_ok=True)
                return YamlContentValidator(root)
            if not root.exists():
                shutil.copytree(_FIXTURE_ROOT, root)
                if scenario == "invalid":
                    for name in ("fixtures", "texts"):
                        edit(
                            root,
                            f"{_SEASON}/{name}.yaml",
                            lambda data: data.update(unexpected=True),
                        )
                elif scenario == "pending":
                    edit(
                        root,
                        f"{_SEASON}/texts.yaml",
                        lambda data: data["texts"][0].update(status="draft", reviewed_by=None),
                    )
            return YamlContentValidator(root)

        return make
