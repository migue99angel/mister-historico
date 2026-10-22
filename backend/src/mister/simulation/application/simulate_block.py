"""Use case: simulate one block. Implemented in T2.6; `SimulationService` already delegates here
so T2.6 never has to touch the published `api.py`."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mister.shared_kernel.randomness import RandomSource
    from mister.simulation.application.api import BlockSimRequest, BlockSummaryDTO


def simulate_block(request: BlockSimRequest, rng: RandomSource) -> BlockSummaryDTO:
    """Simulate the fixtures of the block in date order (see `SimulationService`)."""
    raise NotImplementedError("simulate_block is implemented in T2.6")
