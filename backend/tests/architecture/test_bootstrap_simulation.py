"""The composition root constructs Simulation through its published API."""

import ast
from pathlib import Path

from tests.architecture.test_layer_contracts import R7, _lint


def test_bootstrap_imports_simulation_service_from_its_published_api() -> None:
    bootstrap = Path(__file__).resolve().parents[2] / "src/mister/bootstrap.py"
    tree = ast.parse(bootstrap.read_text())
    providers = [
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
        if alias.name == "SimulationService"
    ]

    assert providers == ["mister.simulation.application.api"]


def test_bootstrap_may_import_the_simulation_api(tmp_path: Path) -> None:
    result = _lint(
        tmp_path,
        {"bootstrap.py": "from fakepkg.simulation.application import api\n"},
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert f"{R7} KEPT" in result.stdout


def test_bootstrap_must_not_import_simulation_application_internals(tmp_path: Path) -> None:
    result = _lint(
        tmp_path,
        {"bootstrap.py": "from fakepkg.simulation.application import internal\n"},
    )

    assert result.returncode != 0, result.stdout + result.stderr
    assert f"{R7} BROKEN" in result.stdout
