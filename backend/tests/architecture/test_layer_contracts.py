"""The import-linter layer rules (PLAN §3.2) really work.

There are no contexts in `mister` yet, so the real contracts pass without checking
anything. To prove they bite, the contracts in `pyproject.toml` are copied with the root
package renamed to a fake package with the same shape, and `lint-imports` is run on it.
"""

import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_REAL_ROOT = "mister"
_FAKE_ROOT = "fakepkg"
_LINT_IMPORTS = Path(sys.executable).parent / "lint-imports"

# Clean package: every layer imports only what it is allowed to.
_CLEAN_PACKAGE: dict[str, str] = {
    "__init__.py": "",
    "bootstrap.py": "from fakepkg.ctx.infrastructure import repo\n",
    "shared_kernel/__init__.py": "",
    "shared_kernel/ids.py": "import uuid\n",
    "ctx/__init__.py": "",
    "ctx/domain/__init__.py": "",
    "ctx/domain/model.py": "import dataclasses\nfrom fakepkg.shared_kernel import ids\n",
    "ctx/application/__init__.py": "",
    "ctx/application/use_case.py": "from fakepkg.ctx.domain import model\n",
    "ctx/infrastructure/__init__.py": "",
    "ctx/infrastructure/repo.py": (
        "import sqlalchemy\nfrom fakepkg.ctx.application import use_case\n"
    ),
    "other/__init__.py": "",
    "other/domain/__init__.py": "",
    "other/domain/model.py": "from fakepkg.shared_kernel import ids\n",
    "other/application/__init__.py": "",
    "entrypoints/__init__.py": "",
    "entrypoints/api/__init__.py": "",
    "entrypoints/api/app.py": "import fastapi\nfrom fakepkg.ctx.application import use_case\n",
}


def _rename_root(value: object) -> object:
    if isinstance(value, str):
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
    with (_BACKEND_ROOT / "pyproject.toml").open("rb") as file:
        config = _rename_root(tomllib.load(file)["tool"]["importlinter"])
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
    assert "0 broken" in result.stdout


@pytest.mark.parametrize(
    ("module", "source"),
    [
        pytest.param("ctx/domain/bad.py", "import sqlalchemy\n", id="domain-imports-sqlalchemy"),
        pytest.param("ctx/domain/bad.py", "import pydantic\n", id="domain-imports-pydantic"),
        pytest.param("ctx/domain/bad.py", "import fastapi\n", id="domain-imports-fastapi"),
        pytest.param(
            "ctx/domain/bad.py",
            "from fakepkg.ctx.application import use_case\n",
            id="domain-imports-application",
        ),
        pytest.param(
            "ctx/domain/bad.py",
            "from fakepkg.ctx.infrastructure import repo\n",
            id="domain-imports-infrastructure",
        ),
        pytest.param(
            "ctx/domain/bad.py",
            "from fakepkg.other.domain import model\n",
            id="domain-imports-another-context-domain",
        ),
        pytest.param(
            "ctx/application/bad.py",
            "from fakepkg.ctx.infrastructure import repo\n",
            id="application-imports-infrastructure",
        ),
        pytest.param(
            "ctx/application/bad.py",
            "from fakepkg.entrypoints.api import app\n",
            id="application-imports-entrypoints",
        ),
        pytest.param(
            "entrypoints/api/bad.py",
            "from fakepkg.ctx.infrastructure import repo\n",
            id="entrypoints-import-infrastructure",
        ),
        pytest.param(
            "entrypoints/api/bad.py",
            "from fakepkg.ctx.domain import model\n",
            id="entrypoints-import-domain",
        ),
        pytest.param(
            "other/application/bad.py",
            "from fakepkg.ctx.infrastructure import repo\n",
            id="another-context-imports-infrastructure",
        ),
    ],
)
def test_forbidden_import_breaks_a_layer_contract(tmp_path: Path, module: str, source: str) -> None:
    result = _lint(tmp_path, {module: source})

    assert result.returncode != 0, result.stdout + result.stderr
    assert "BROKEN" in result.stdout
