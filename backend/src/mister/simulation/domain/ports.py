"""Pure strategies of the engine (no IO). Implementations arrive in T2.1; callers receive them
by parameter, like the `RandomSource` of the shared kernel."""

from typing import Protocol

from mister.shared_kernel.randomness import RandomSource
from mister.simulation.domain.league_types import ExternalResultsRequest, LeagueRow
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


class ExternalResultsPolicy(Protocol):
    """Pure accumulated-results strategy, without IO, randomness or table ranking."""

    def standings(self, request: ExternalResultsRequest) -> tuple[LeagueRow, ...]:
        """Return all participants once, in the original historical baseline row order.

        P2 implementations subtract each historical managed result and add its simulated
        replacement to both sides, using the configured point rules and adjusting W/D/L,
        goals and points. They reject a baseline unable to contain the replaced results.
        Every call uses the original baseline and all replacements through the cutoff;
        applying replacements again to adjusted rows is outside this contract.

        This method never resolves ties. LeagueTable owns ranking and requires complete
        head-to-head evidence when its configured criteria need a managed-team mini-table.
        """
        ...
