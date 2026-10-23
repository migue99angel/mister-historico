"""Run with PYTHONPATH=src .venv/bin/python tests/simulation/unit/benchmark_match_simulator.py.

The 50 ms budget measures 1,000 simulations on the real seeded source, without coverage.
Fixture construction is outside the measured region; stream derivation and sampling are inside.
"""

import json
from datetime import date
from statistics import median
from time import perf_counter
from typing import TypedDict

from mister.shared_kernel.ids import ClubSeasonId, CompetitionId, FixtureId
from mister.shared_kernel.randomness import StdlibRandomSource
from mister.shared_kernel.seed import Seed
from mister.simulation.domain.match_simulator import PoissonMatchSimulator
from mister.simulation.domain.model import CompetitionParams, FixtureSpec, MatchSetup, TeamStrength

_MATCHES = 1_000
_ROUNDS = 7
_BUDGET_MS = 50.0


class _Measurement(TypedDict):
    matches: int
    samples_ms: list[float]
    median_ms: float
    budget_ms: float


def main() -> None:
    setups = [
        MatchSetup(
            FixtureSpec(
                FixtureId(f"benchmark-{index}"),
                date(2000, 9, 3),
                CompetitionId("liga-test"),
                ClubSeasonId("test-fc-2000-01"),
                ClubSeasonId("demo-athletic-2000-01"),
            ),
            TeamStrength(1.2, 0.8),
            TeamStrength(0.9, 1.1),
            CompetitionParams(1.3, 1.15),
        )
        for index in range(_MATCHES)
    ]
    simulator = PoissonMatchSimulator()
    rng = StdlibRandomSource(Seed(20261023))
    report: dict[str, _Measurement] = {}
    for decisive in (False, True):
        for setup in setups:  # Warm up before recording the repeated measurements.
            simulator.simulate(setup, rng, decisive=decisive)
        samples = []
        for _ in range(_ROUNDS):
            start = perf_counter()
            for setup in setups:
                simulator.simulate(setup, rng, decisive=decisive)
            samples.append((perf_counter() - start) * 1_000)
        report["decisive" if decisive else "regulation"] = {
            "matches": _MATCHES,
            "samples_ms": samples,
            "median_ms": median(samples),
            "budget_ms": _BUDGET_MS,
        }
    print(json.dumps(report, indent=2))  # noqa: T201 - standalone benchmark report
    if any(measurement["median_ms"] >= _BUDGET_MS for measurement in report.values()):
        raise SystemExit("Median simulation time exceeds the 50 ms budget")


if __name__ == "__main__":
    main()
