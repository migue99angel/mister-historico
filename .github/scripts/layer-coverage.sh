#!/usr/bin/env bash
# Enforce the per-layer coverage threshold from PLAN §4.3: domain + application of every
# backend context must reach >= 95 % (lines + branches; `branch = true` in pyproject.toml).
#
# Run from `backend/` after pytest has written the `.coverage` data file.
# While no context has domain/application modules yet, coverage prints "No data to report."
# and exits with 1: that case (and only that one) is skipped explicitly.
set -uo pipefail

INCLUDE="${LAYER_COVERAGE_INCLUDE:-src/mister/*/domain/*,src/mister/*/application/*}"
THRESHOLD="${LAYER_COVERAGE_THRESHOLD:-95}"

output="$(uv run coverage report --include="${INCLUDE}" --fail-under="${THRESHOLD}" 2>&1)"
status=$?
echo "${output}"

if [[ ${status} -ne 0 ]] && grep -q "No data to report" <<<"${output}"; then
  echo "::notice title=Layer coverage::No domain/application modules yet; skipping the ${THRESHOLD} % threshold."
  exit 0
fi
if [[ ${status} -ne 0 ]]; then
  echo "::error title=Layer coverage::domain + application coverage is below ${THRESHOLD} % (or coverage failed)."
fi
exit "${status}"
