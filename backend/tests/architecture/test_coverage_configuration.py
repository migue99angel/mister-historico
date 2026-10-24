"""Coverage exclusions keep executable tuple annotations and their missing branches."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

_CONFIG = Path(__file__).resolve().parents[2] / "pyproject.toml"
_SOURCE = """def values(include: bool) -> tuple[int, ...]:
    if include:
        return (1,)
    return ()

class Contract:
    def pending(self) -> int:
        ...

assert values(True) == (1,)
"""


@pytest.fixture
def measured_module(tmp_path: Path) -> dict[str, Any]:
    module = tmp_path / "sample.py"
    module.write_text(_SOURCE)
    data_file = tmp_path / ".coverage"
    report_file = tmp_path / "coverage.json"
    commands = (
        [
            "run",
            "--branch",
            f"--source={tmp_path}",
            str(module),
        ],
        ["json", "--fail-under=0", "-o", str(report_file)],
    )
    for command in commands:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "coverage",
                command[0],
                f"--rcfile={_CONFIG}",
                f"--data-file={data_file}",
                *command[1:],
            ],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
    report: dict[str, Any] = json.loads(report_file.read_text())
    module_report: dict[str, Any] = report["files"]["sample.py"]
    return module_report


def test_tuple_annotations_do_not_hide_executable_lines_or_missing_branches(
    measured_module: dict[str, Any],
) -> None:
    assert {1, 2, 3} <= set(measured_module["executed_lines"])
    assert measured_module["missing_lines"] == [4]
    assert measured_module["missing_branches"] == [[2, 4]]
    assert measured_module["summary"]["num_branches"] == 2
    assert measured_module["summary"]["missing_branches"] == 1


def test_a_standalone_ellipsis_stub_body_remains_excluded(
    measured_module: dict[str, Any],
) -> None:
    assert 8 in measured_module["excluded_lines"]
    assert 8 not in measured_module["missing_lines"]
