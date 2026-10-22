"""Pure strategies of the engine (no IO). Implementations arrive in T2.1; callers receive them
by parameter, like the `RandomSource` of the shared kernel."""

from typing import Protocol

from mister.shared_kernel.randomness import RandomSource
from mister.simulation.domain.model import (
    CompetitionParams,
    MatchResult,
    MatchSetup,
    Score,
    TeamStrength,
    Venue,
)


class GoalModel(Protocol):
    """Expected goals (lambda, ADR-004). A pure function: it never uses randomness."""

    def expected_goals(
        self,
        team: TeamStrength,
        opponent: TeamStrength,
        venue: Venue,
        params: CompetitionParams,
        *,
        extra_time: bool = False,
    ) -> float:
        """Lambda of `team` against `opponent`; `venue` is the ground from `team`'s point of
        view. With `extra_time`, the lambda of the 30 extra minutes (a third of 90)."""
        ...


class MatchSimulator(Protocol):
    """Draws match outcomes from derived streams of the root source (ADR-005 key table)."""

    def simulate(
        self, setup: MatchSetup, rng: RandomSource, *, decisive: bool = False
    ) -> MatchResult:
        """Play the fixture: 90 minutes from `rng.stream("match", fixture_id, "goals", side)`;
        if `decisive` and level, extra time and a shootout too."""
        ...

    def extra_time(self, setup: MatchSetup, rng: RandomSource) -> Score:
        """Goals of the extra 30 minutes, from `("match", fixture_id, "extra_time", side)`.
        Called when the tie is level on aggregate, even if this match was not level."""
        ...

    def penalty_shootout(self, setup: MatchSetup, rng: RandomSource) -> Score:
        """A shootout that cannot end level, from `("match", fixture_id, "penalties")`.
        Called when the tie is still level after extra time (or when there is none)."""
        ...
