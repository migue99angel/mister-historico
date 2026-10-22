"""Shared pytest configuration.

Every test is marked automatically after the test-level directory it lives in, at any depth
(`tests/integration/`, `tests/contracts/`, `tests/simulation/unit/`...). Tests outside any
level directory are marked `unit`. A test can still add explicit markers on top.
"""

from pathlib import Path

import pytest

_TESTS_ROOT = Path(__file__).parent
_LEVEL_DIRS: dict[str, str] = {
    "unit": "unit",
    "integration": "integration",
    "contract": "contract",
    "contracts": "contract",
    "calibration": "calibration",
    "content": "content",
    "e2e": "e2e",
}


def _level_marker(test_path: Path) -> str:
    try:
        directories = test_path.relative_to(_TESTS_ROOT).parts[:-1]
    except ValueError:
        return "unit"
    for directory in directories:
        if directory in _LEVEL_DIRS:
            return _LEVEL_DIRS[directory]
    return "unit"


# tryfirst: markers must be in place before `-m` deselects anything.
@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        item.add_marker(_level_marker(item.path))
