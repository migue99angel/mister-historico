"""Configuración común de pytest.

Marca automáticamente cada test según la carpeta de nivel en la que vive
(`tests/integration/`, `tests/contract/`...). Lo que no está en ninguna de esas
carpetas se considera `unit`. Un test puede añadir además marcadores explícitos.
"""

from pathlib import Path

import pytest

_TESTS_ROOT = Path(__file__).parent
_LEVEL_DIRS = frozenset({"integration", "contract", "calibration", "content", "e2e"})


# tryfirst: los marcadores tienen que estar puestos antes de que `-m` deseleccione.
@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        try:
            relative = item.path.relative_to(_TESTS_ROOT)
        except ValueError:
            continue
        level = relative.parts[0] if len(relative.parts) > 1 else ""
        item.add_marker(level if level in _LEVEL_DIRS else "unit")
