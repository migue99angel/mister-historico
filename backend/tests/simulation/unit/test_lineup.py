"""Position-preserving deterministic selection using invented Test FC players."""

from dataclasses import replace

import pytest

from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import PlayerId
from mister.simulation.domain.lineup import effective_rating, select_lineup
from mister.simulation.domain.model import (
    Fitness,
    Morale,
    Position,
    Priority,
    Rating,
    SimPlayer,
    Style,
    Tactic,
)


def squad() -> tuple[SimPlayer, ...]:
    """Eleven starters and one reserve per line; entirely synthetic."""
    positions = [Position.GK, *[Position.DF] * 4, *[Position.MF] * 4, *[Position.FW] * 2]
    starters = tuple(
        SimPlayer(PlayerId(f"starter-{i:02}"), pos, Rating(80)) for i, pos in enumerate(positions)
    )
    reserves = tuple(
        SimPlayer(PlayerId(f"reserve-{pos.value.lower()}"), pos, Rating(60)) for pos in Position
    )
    return (*starters, *reserves)


TACTIC = Tactic(Style.BALANCED, "4-4-2")


def test_an_injured_player_never_starts() -> None:
    players = squad()
    injured = replace(players[0], injured=True, rating=Rating(99))
    lineup = select_lineup((injured, *players[1:]), TACTIC)
    assert injured.player_id not in {entry.player.player_id for entry in lineup.starters}


def test_low_fitness_can_put_a_reserve_ahead_of_a_starter() -> None:
    players = squad()
    exhausted = replace(players[0], fitness=Fitness(0), rating=Rating(65))
    lineup = select_lineup((exhausted, *players[1:]), TACTIC)
    assert lineup.starters[0].player.player_id == PlayerId("reserve-gk")


@pytest.mark.parametrize(
    ("priority", "rotations"), [(Priority.HIGH, 0), (Priority.NORMAL, 2), (Priority.LOW, 4)]
)
def test_priority_rotates_the_requested_number_when_feasible(
    priority: Priority, rotations: int
) -> None:
    baseline = select_lineup(squad(), TACTIC)
    lineup = select_lineup(squad(), TACTIC, priority=priority)
    before = {entry.player.player_id for entry in baseline.starters}
    after = {entry.player.player_id for entry in lineup.starters}
    assert len(after - before) == rotations
    assert lineup.rotated == rotations
    assert all(entry.position is entry.player.position for entry in lineup.starters)


def test_rotation_is_limited_to_the_available_reserves() -> None:
    lineup = select_lineup(squad()[:12], TACTIC, priority=Priority.LOW)
    assert lineup.rotated == 1


def test_rotation_does_not_sacrifice_a_position_without_a_replacement() -> None:
    players = squad()[:11]
    reserves = tuple(
        SimPlayer(PlayerId(f"extra-fw-{i}"), Position.FW, Rating(60)) for i in range(4)
    )
    lineup = select_lineup((*players, *reserves), TACTIC, priority=Priority.LOW)
    assert lineup.rotated == 2
    assert all(entry.position is entry.player.position for entry in lineup.starters)


def test_selection_reserves_scarce_positions_before_filling_a_missing_goalkeeper() -> None:
    players = tuple(player for player in squad() if player.position is not Position.GK)
    lineup = select_lineup(players, TACTIC)
    assert sum(entry.position is not entry.player.position for entry in lineup.starters) == 1
    assert all(entry.player.position is Position.DF for entry in lineup.starters[1:5])
    goalkeeper = lineup.starters[0]
    assert goalkeeper.effective_rating == effective_rating(goalkeeper.player) - 5


def test_out_of_position_rating_stays_in_the_rating_range() -> None:
    players = tuple(
        replace(player, position=Position.MF, rating=Rating(1)) for player in squad()[:11]
    )
    assert all(entry.effective_rating == 1 for entry in select_lineup(players, TACTIC).starters)


@pytest.mark.parametrize(
    ("system", "counts"),
    [("4-2-3-1", (1, 4, 5, 1)), ("4-1-4-1", (1, 4, 5, 1)), ("3-4-3", (1, 3, 4, 3))],
)
def test_all_middle_system_numbers_are_midfielders(system: str, counts: tuple[int, ...]) -> None:
    lineup = select_lineup(squad(), Tactic(Style.BALANCED, system))
    assert (
        tuple(sum(entry.position is pos for entry in lineup.starters) for pos in Position) == counts
    )


@pytest.mark.parametrize("priority", list(Priority))
def test_ties_are_broken_by_id_independently_of_roster_order(priority: Priority) -> None:
    assert select_lineup(squad(), TACTIC, priority=priority) == select_lineup(
        tuple(reversed(squad())), TACTIC, priority=priority
    )


def test_fewer_than_eleven_healthy_players_cannot_form_a_lineup() -> None:
    with pytest.raises(InvalidValueError, match="healthy"):
        select_lineup(tuple(replace(player, injured=True) for player in squad()), TACTIC)


@pytest.mark.parametrize(
    ("fitness", "morale", "expected"),
    [(100, 50, 70), (90, 50, 70), (0, 50, 63.7), (100, 0, 68), (100, 100, 72)],
)
def test_effective_rating_uses_the_exact_adr_formula(
    fitness: int, morale: int, expected: float
) -> None:
    player = replace(squad()[0], rating=Rating(70), fitness=Fitness(fitness), morale=Morale(morale))
    assert effective_rating(player) == pytest.approx(expected)


@pytest.mark.parametrize(("rating", "morale", "expected"), [(1, 0, 1), (99, 100, 99)])
def test_effective_rating_is_clamped(rating: int, morale: int, expected: float) -> None:
    assert (
        effective_rating(replace(squad()[0], rating=Rating(rating), morale=Morale(morale)))
        == expected
    )


def test_duplicate_player_ids_cannot_fill_two_slots() -> None:
    players = squad()
    with pytest.raises(InvalidValueError, match="distinct"):
        select_lineup((*players, players[0]), TACTIC)


@pytest.mark.parametrize("priority", list(Priority))
def test_required_reserve_starts_under_every_rotation_priority(priority: Priority) -> None:
    required = PlayerId("reserve-fw")
    lineup = select_lineup(squad(), TACTIC, priority=priority, required=frozenset({required}))
    assert required in {entry.player.player_id for entry in lineup.starters}
    assert len(lineup.starters) == 11


@pytest.mark.parametrize(
    "required", [frozenset({PlayerId("missing")}), frozenset(p.player_id for p in squad()[:12])]
)
def test_incompatible_required_starters_are_rejected(required: frozenset[PlayerId]) -> None:
    with pytest.raises(InvalidValueError):
        select_lineup(squad(), TACTIC, required=required)


def test_an_injured_required_player_is_rejected_without_changing_injury() -> None:
    players = squad()
    injured = replace(players[-1], injured=True)
    with pytest.raises(InvalidValueError):
        select_lineup((*players[:-1], injured), TACTIC, required=frozenset({injured.player_id}))
    assert injured.injured


@pytest.mark.parametrize("seed", range(12))
@pytest.mark.parametrize("priority", list(Priority))
def test_constrained_selection_matches_exhaustive_native_coverage_and_rotation(
    seed: int,
    priority: Priority,
) -> None:
    from itertools import combinations

    from mister.shared_kernel.randomness import StdlibRandomSource
    from mister.shared_kernel.seed import Seed

    rng = StdlibRandomSource(Seed(seed))
    players = tuple(
        SimPlayer(
            PlayerId(f"test-{i:02}"),
            rng.choice(tuple(Position)),
            Rating(rng.choice(tuple(range(40, 91)))),
        )
        for i in range(14)
    )
    required = frozenset({players[-1].player_id})
    counts = {Position.GK: 1, Position.DF: 4, Position.MF: 4, Position.FW: 2}
    choices = tuple(c for c in combinations(players, 11) if required <= {p.player_id for p in c})

    def objective(choice: tuple[SimPlayer, ...]) -> tuple[int, int, tuple[str, ...]]:
        return (
            -sum(min(counts[pos], sum(p.position is pos for p in choice)) for pos in Position),
            -sum(p.rating.value for p in choice),
            tuple(sorted(p.player_id.value for p in choice)),
        )

    baseline = min(choices, key=objective)
    regulars = {p.player_id for p in baseline}
    target = {Priority.HIGH: 0, Priority.NORMAL: 2, Priority.LOW: 4}[priority]
    eligible = [
        c
        for c in choices
        if objective(c)[0] == objective(baseline)[0]
        and len({p.player_id for p in c} - regulars) <= target
    ]
    rotation = max(len({p.player_id for p in c} - regulars) for c in eligible)
    expected = min(
        (c for c in eligible if len({p.player_id for p in c} - regulars) == rotation), key=objective
    )
    actual = select_lineup(players, TACTIC, priority=priority, required=required)
    assert {p.player.player_id for p in actual.starters} == {p.player_id for p in expected}
    assert actual.rotated == rotation
