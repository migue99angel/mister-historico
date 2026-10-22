#!/usr/bin/env bash
# Enforce the per-layer coverage threshold from PLAN §4.3: domain + application of every
# backend context must reach >= 95 % of lines AND >= 95 % of branches, checked separately
# (`coverage report --fail-under` would only check the combined total).
#
# Run from `backend/` after pytest has written the `.coverage` data file.
#
# Whether to skip is decided from the files on disk, never from coverage's output: the check
# is skipped only while no context has domain/application modules. As soon as one exists,
# the coverage data must exist, report modules, and include every module on disk.
set -euo pipefail
shopt -s globstar nullglob

THRESHOLD="${LAYER_COVERAGE_THRESHOLD:-95}"
INCLUDE="${LAYER_COVERAGE_INCLUDE:-src/mister/*/domain/*,src/mister/*/application/*}"

modules=(src/mister/*/domain/**/*.py src/mister/*/application/**/*.py)

if [[ ${#modules[@]} -eq 0 ]]; then
  echo "::notice title=Layer coverage::No domain/application modules yet; skipping the ${THRESHOLD} % threshold."
  exit 0
fi

fail() {
  echo "::error title=Layer coverage::$1"
  exit 1
}

echo "Found ${#modules[@]} domain/application module(s)."
[[ -f .coverage ]] || fail "No .coverage data file in $(pwd): run pytest with coverage first."

report="$(mktemp)"
trap 'rm -f "${report}"' EXIT
# --fail-under=0: the global fail_under from pyproject.toml must not fail this report.
uv run coverage json --include="${INCLUDE}" --fail-under=0 -o "${report}" \
  || fail "coverage json failed (no data?) for --include='${INCLUDE}'."

# Inline Python reads the JSON report; the module list comes from the glob above.
uv run python - "${report}" "${THRESHOLD}" "${modules[@]}" <<'PY'
import json
import sys

report_path, threshold, *on_disk = sys.argv[1:]
threshold_value = float(threshold)
with open(report_path, encoding="utf-8") as handle:
    report = json.load(handle)

files = report.get("files", {})
if not files:
    print("::error title=Layer coverage::The coverage report contains no modules.")
    sys.exit(1)

missing = sorted(set(on_disk) - set(files))
if missing:
    print("::error title=Layer coverage::Modules missing from the coverage report: " + ", ".join(missing))
    sys.exit(1)

totals = report["totals"]
lines = 100.0 * totals["covered_lines"] / totals["num_statements"] if totals["num_statements"] else 100.0
branches = (
    100.0 * totals["covered_branches"] / totals["num_branches"] if totals["num_branches"] else 100.0
)
print(f"domain + application: lines {lines:.2f} %, branches {branches:.2f} % (threshold {threshold_value:g} %)")

failed = [name for name, value in (("lines", lines), ("branches", branches)) if value < threshold_value]
if failed:
    print(f"::error title=Layer coverage::{' and '.join(failed)} below {threshold_value:g} %.")
    sys.exit(2)
PY
