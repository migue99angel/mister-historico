"""The import-linter layer rules (PLAN §3.2) really work.

There are no contexts in `mister` yet, so the real contracts pass without checking
anything. To prove they bite, the contracts in `pyproject.toml` are copied with the root
package renamed to a fake package with the same shape, and `lint-imports` is run on it.
"""

import json
import os
import re
import subprocess
import sys
import tomllib
from importlib.metadata import packages_distributions
from pathlib import Path
from typing import Any

import pytest

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_REAL_ROOT = "mister"
_FAKE_ROOT = "fakepkg"
_LINT_IMPORTS = Path(sys.executable).parent / "lint-imports"

R0 = "R0 shared_kernel only imports the stdlib"
R1 = "R1 domain only imports the stdlib and shared_kernel"
R2 = "R2 application does not import infrastructure or entrypoints"
R3 = "R3 infrastructure is only imported by bootstrap"
R4 = "R4 domains of different contexts are independent"
R5 = "R5 entrypoints do not import domain or infrastructure directly"
R6 = "R6 only simulation itself imports simulation.domain"
R7 = "R7 only simulation.application.api is public"

# Clean package: every layer imports only what it is allowed to.
_CLEAN_PACKAGE: dict[str, str] = {
    "__init__.py": "",
    "bootstrap.py": (
        "from fakepkg.ctx.infrastructure import repo\n"
        "from fakepkg.shared_kernel.infrastructure import rng\n"
    ),
    "settings.py": "import pydantic_settings\n",
    "shared_kernel/__init__.py": "",
    "shared_kernel/ids.py": "import uuid\nfrom dataclasses import dataclass\n",
    "shared_kernel/random.py": (
        "from typing import Protocol\nfrom fakepkg.shared_kernel import ids\n"
    ),
    # Shared kernel adapters may use external libraries.
    "shared_kernel/infrastructure/__init__.py": "import numpy\n",
    "shared_kernel/infrastructure/rng.py": (
        "import numpy\nfrom fakepkg.shared_kernel import random\n"
    ),
    "ctx/__init__.py": "",
    "ctx/domain/__init__.py": "",
    "ctx/domain/model.py": "import dataclasses\nfrom fakepkg.shared_kernel import ids, random\n",
    "ctx/application/__init__.py": "",
    "ctx/application/use_case.py": "from fakepkg.ctx.domain import model\n",
    "ctx/infrastructure/__init__.py": "",
    "ctx/infrastructure/repo.py": (
        "import sqlalchemy\nimport yaml\nfrom fakepkg.ctx.application import use_case\n"
    ),
    "other/__init__.py": "",
    "other/domain/__init__.py": "",
    "other/domain/model.py": "from fakepkg.shared_kernel import ids\n",
    "other/application/__init__.py": "",
    # `simulation` publishes `application/api.py`; `game` consumes it from its infrastructure.
    "simulation/__init__.py": "",
    "simulation/domain/__init__.py": "",
    "simulation/domain/model.py": "from fakepkg.shared_kernel import ids\n",
    "simulation/application/__init__.py": "",
    "simulation/application/api.py": "from fakepkg.simulation.domain import model\n",
    "simulation/application/internal.py": "from fakepkg.simulation.domain import model\n",
    "simulation/infrastructure/__init__.py": "",
    "simulation/infrastructure/adapter.py": (
        "from fakepkg.simulation.application import api\n"
        "from fakepkg.simulation.domain import model\n"
    ),
    "game/__init__.py": "",
    "game/domain/__init__.py": "",
    "game/application/__init__.py": "",
    "game/infrastructure/__init__.py": "",
    "game/infrastructure/simulation_adapter.py": (
        "from fakepkg.simulation.application import api\n"
    ),
    "entrypoints/__init__.py": "",
    "entrypoints/api/__init__.py": "",
    "entrypoints/api/app.py": (
        "import fastapi\n"
        "from fakepkg import bootstrap\n"
        "from fakepkg.ctx.application import use_case\n"
    ),
}


def _load_importlinter_config() -> dict[str, Any]:
    with (_BACKEND_ROOT / "pyproject.toml").open("rb") as file:
        config: dict[str, Any] = tomllib.load(file)["tool"]["importlinter"]
    return config


def _rename_root(value: object) -> object:
    if isinstance(value, str):
        # Import expressions in `ignore_imports` look like "mister.x -> y": rename both sides.
        if " -> " in value:
            importer, imported = value.split(" -> ")
            return f"{_rename_root(importer)} -> {_rename_root(imported)}"
        if value == _REAL_ROOT or value.startswith(f"{_REAL_ROOT}."):
            return _FAKE_ROOT + value.removeprefix(_REAL_ROOT)
        return value
    if isinstance(value, list):
        return [_rename_root(item) for item in value]
    if isinstance(value, dict):
        return {key: _rename_root(item) for key, item in value.items()}
    return value


def _toml_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    # JSON strings and lists of strings are valid TOML.
    return json.dumps(value)


def _write_config(path: Path) -> None:
    config = _rename_root(_load_importlinter_config())
    assert isinstance(config, dict)
    contracts = config.pop("contracts")
    lines = ["[tool.importlinter]"]
    lines += [f"{key} = {_toml_value(value)}" for key, value in config.items()]
    for contract in contracts:
        lines += ["", "[[tool.importlinter.contracts]]"]
        lines += [f"{key} = {_toml_value(value)}" for key, value in contract.items()]
    path.write_text("\n".join(lines) + "\n")


def _lint(tmp_path: Path, extra_modules: dict[str, str]) -> subprocess.CompletedProcess[str]:
    for relative, source in {**_CLEAN_PACKAGE, **extra_modules}.items():
        module = tmp_path / _FAKE_ROOT / relative
        module.parent.mkdir(parents=True, exist_ok=True)
        module.write_text(source)
    config = tmp_path / "importlinter.toml"
    _write_config(config)
    return subprocess.run(
        [str(_LINT_IMPORTS), "--config", str(config), "--no-cache"],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(tmp_path)},
        capture_output=True,
        text=True,
        check=False,
    )


def test_clean_package_keeps_every_layer_contract(tmp_path: Path) -> None:
    result = _lint(tmp_path, {})

    assert result.returncode == 0, result.stdout + result.stderr
    for contract in (R0, R1, R2, R3, R4, R5, R6, R7):
        assert f"{contract} KEPT" in result.stdout


def _case(module: str, source: str, contract: str, case_id: str) -> Any:
    return pytest.param(module, source, contract, id=case_id)


@pytest.mark.parametrize(
    ("module", "source", "contract"),
    [
        _case("ctx/domain/bad.py", "import sqlalchemy\n", R1, "domain-imports-sqlalchemy"),
        _case("ctx/domain/bad.py", "import pydantic\n", R1, "domain-imports-pydantic"),
        _case("ctx/domain/bad.py", "import fastapi\n", R1, "domain-imports-fastapi"),
        _case("ctx/domain/bad.py", "import yaml\n", R1, "domain-imports-yaml"),
        _case("ctx/domain/bad.py", "from PIL import Image\n", R1, "domain-imports-pil"),
        _case("ctx/domain/bad.py", "import httpx\n", R1, "domain-imports-httpx"),
        _case("ctx/domain/bad.py", "import numpy\n", R1, "domain-imports-numpy"),
        _case(
            "ctx/domain/bad.py",
            "from fakepkg.ctx.application import use_case\n",
            R1,
            "domain-imports-application",
        ),
        _case(
            "ctx/domain/bad.py",
            "from fakepkg.ctx.infrastructure import repo\n",
            R1,
            "domain-imports-infrastructure",
        ),
        _case(
            "ctx/domain/bad.py",
            "from fakepkg.shared_kernel.infrastructure import rng\n",
            R1,
            "domain-imports-shared-kernel-infrastructure",
        ),
        _case(
            "ctx/domain/bad.py",
            "from fakepkg.other.domain import model\n",
            R4,
            "domain-imports-another-context-domain",
        ),
        _case(
            "ctx/application/bad.py",
            "from fakepkg.ctx.infrastructure import repo\n",
            R2,
            "application-imports-infrastructure",
        ),
        _case(
            "ctx/application/bad.py",
            "from fakepkg.entrypoints.api import app\n",
            R2,
            "application-imports-entrypoints",
        ),
        _case(
            "other/application/bad.py",
            "from fakepkg.ctx.infrastructure import repo\n",
            R3,
            "another-context-imports-infrastructure",
        ),
        _case(
            "entrypoints/api/bad.py",
            "from fakepkg.ctx.infrastructure import repo\n",
            R5,
            "entrypoints-import-infrastructure",
        ),
        _case(
            "entrypoints/api/bad.py",
            "from fakepkg.ctx.domain import model\n",
            R5,
            "entrypoints-import-domain",
        ),
        _case(
            "game/application/bad.py",
            "from fakepkg.simulation.domain import model\n",
            R6,
            "another-context-application-imports-simulation-domain",
        ),
        _case(
            "game/infrastructure/bad.py",
            "import fakepkg.simulation.domain.model\n",
            R6,
            "another-context-infrastructure-imports-simulation-domain-module",
        ),
        _case(
            "game/domain/bad.py",
            "from fakepkg.simulation.domain import model\n",
            R6,
            "another-context-domain-imports-simulation-domain",
        ),
        _case(
            "entrypoints/api/bad.py",
            "from fakepkg.simulation.domain import model\n",
            R6,
            "entrypoints-import-simulation-domain",
        ),
        _case(
            "bootstrap.py",
            "from fakepkg.simulation.domain import model\n",
            R6,
            "bootstrap-imports-simulation-domain",
        ),
        _case(
            "game/infrastructure/bad.py",
            "from fakepkg.simulation.application import internal\n",
            R7,
            "another-context-infrastructure-imports-simulation-internals",
        ),
        _case(
            "game/application/bad.py",
            "from fakepkg.simulation.application import api\n",
            R7,
            "another-context-application-imports-simulation-api",
        ),
        _case(
            "game/domain/bad.py",
            "from fakepkg.simulation.application import api\n",
            R7,
            "another-context-domain-imports-simulation-api",
        ),
        _case(
            "entrypoints/api/bad.py",
            "from fakepkg.simulation.application import api\n",
            R7,
            "entrypoints-import-simulation-api",
        ),
        _case(
            "shared_kernel/bad.py", "import sqlalchemy\n", R0, "shared-kernel-imports-sqlalchemy"
        ),
        _case("shared_kernel/bad.py", "import numpy\n", R0, "shared-kernel-imports-numpy"),
        _case(
            "shared_kernel/bad.py",
            "from fakepkg.ctx.domain import model\n",
            R0,
            "shared-kernel-imports-a-context-domain",
        ),
        _case(
            "shared_kernel/bad.py",
            "from fakepkg import settings\n",
            R0,
            "shared-kernel-imports-settings",
        ),
        _case(
            "shared_kernel/infrastructure/bad.py",
            "from fakepkg.ctx.domain import model\n",
            R0,
            "shared-kernel-adapter-imports-a-context-domain",
        ),
    ],
)
def test_forbidden_import_breaks_its_layer_contract(
    tmp_path: Path, module: str, source: str, contract: str
) -> None:
    result = _lint(tmp_path, {module: source})

    assert result.returncode != 0, result.stdout + result.stderr
    assert f"{contract} BROKEN" in result.stdout, result.stdout


def _forbidden_modules(contract_name: str) -> set[str]:
    contracts = _load_importlinter_config()["contracts"]
    (contract,) = (c for c in contracts if c["name"] == contract_name)
    return set(contract["forbidden_modules"])


def _runtime_dependency_import_names() -> set[str]:
    with (_BACKEND_ROOT / "pyproject.toml").open("rb") as file:
        requirements: list[str] = tomllib.load(file)["project"]["dependencies"]
    distributions = {re.split(r"[\[<>=!~; ]", req, maxsplit=1)[0].lower() for req in requirements}
    return {
        import_name
        for import_name, owners in packages_distributions().items()
        if not import_name.startswith("_")
        and any(owner.lower().replace("_", "-") in distributions for owner in owners)
    }


@pytest.mark.parametrize("contract", [R0, R1])
def test_every_runtime_dependency_is_forbidden_in_pure_layers(contract: str) -> None:
    """External libraries are forbidden by a blacklist (see pyproject.toml), so any new
    runtime dependency must be added to it; this test fails until it is."""
    missing = _runtime_dependency_import_names() - _forbidden_modules(contract)

    assert not missing, f"add {sorted(missing)} to the forbidden modules of {contract!r}"
