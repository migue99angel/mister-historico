"""Fixture-scoped key starter: requirement, fallback evidence and RNG-free projection."""

import hashlib
from dataclasses import replace
from datetime import date

import pytest
from tests.simulation.unit.benchmark_season import build_test_fc_request
from tests.simulation.unit.test_season_competitions import OwnLoses, cup_request
from tests.simulation.unit.test_simulate_block import (
    END,
    ME,
    START,
    FixedMatches,
    continuation,
    play,
    request,
)

from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import FixtureId, PlayerId
from mister.shared_kernel.randomness import StdlibRandomSource
from mister.shared_kernel.seed import Seed
from mister.simulation.application.api import (
    BlockSimRequest,
    BlockSummaryDTO,
    ForcedInjuryDTO,
    KeyStarterOutcome,
    KeyStarterSelection,
    LineupProjectionDTO,
    SimulationService,
    SquadMembershipInput,
    SquadPlayerInput,
)
from mister.simulation.application.simulate_block import _map_request, _simulate
from mister.simulation.domain.lineup import effective_rating, select_lineup
from mister.simulation.domain.model import Priority
from mister.simulation.domain.strength import StrengthReference, calculate_strength

KEY = FixtureId("test-1")
LATER = FixtureId("test-3")
# The two weakest goalkeeper-free reserves of `team()`: never in the default eleven.
RESERVE = PlayerId("test-15")
_GOLDEN_WITHOUT_SELECTION = "0ee2376af5034c9800a7488ebf6ad2722ac0a1b820b43bbc69eeb8eedaf508de"
_GOLDEN_WITH_SELECTION = "a45e2904b423a8e77fae21d22408cb26a19931beca237f51677eb114f2f89dda"


def _with_selection(
    value: BlockSimRequest, player: PlayerId, fixture: FixtureId = KEY, on: date = START
) -> BlockSimRequest:
    return replace(value, key_starter=KeyStarterSelection(fixture, on, player))


def _starters(summary: BlockSummaryDTO) -> tuple[PlayerId, ...]:
    assert summary.key_starter_outcome is not None
    return summary.key_starter_outcome.starter_ids


def _digest(summary: BlockSummaryDTO) -> str:
    data = repr(
        (
            summary.results,
            summary.standings,
            summary.events,
            summary.injuries,
            summary.player_states,
            summary.unresolved_knockout_ties,
        )
    )
    return hashlib.sha256(data.encode()).hexdigest()


def _default_starters(value: BlockSimRequest) -> set[PlayerId]:
    block = _map_request(value)
    squad = block.managed_team.squad or ()
    assert block.managed_team.tactic is not None
    lineup = select_lineup(squad, block.managed_team.tactic, priority=Priority.NORMAL)
    return {item.player.player_id for item in lineup.starters}


class _ExplodingRandom(StdlibRandomSource):
    def stream(self, *keys: object) -> "_ExplodingRandom":
        raise AssertionError("invalid input must be rejected before drawing")


# --------------------------------------------------------------------------- execution


def test_selected_reserve_is_a_required_starter_only_in_the_chosen_fixture() -> None:
    value = request()
    assert RESERVE not in _default_starters(value)

    summary = play(_with_selection(value, RESERVE))

    assert summary.key_starter_outcome == KeyStarterOutcome(
        KEY, START, RESERVE, _starters(summary), None
    )
    assert RESERVE in _starters(summary)
    assert len(_starters(summary)) == 11


def test_selected_player_enters_the_strength_calculation_of_that_fixture() -> None:
    value = _with_selection(request(), RESERVE)
    spy = FixedMatches()

    play(value, spy)

    block = _map_request(value)
    squad = block.managed_team.squad or ()
    assert block.managed_team.tactic is not None
    forced = select_lineup(
        squad, block.managed_team.tactic, priority=Priority.NORMAL, required=frozenset({RESERVE})
    )
    reference = StrengthReference.from_teams(block.references)
    expected = calculate_strength(block.managed_team, reference, lineup=forced)
    assert spy.setups[0].home == expected


def test_a_selection_for_a_later_fixture_leaves_earlier_fixtures_untouched() -> None:
    value = request()
    base, chosen = FixedMatches(), FixedMatches()

    play(value, base)
    play(_with_selection(value, RESERVE, LATER, END), chosen)

    assert chosen.setups[0] == base.setups[0]
    assert chosen.setups[1] != base.setups[1]


def test_without_selection_the_engine_reports_no_evidence_and_keeps_the_golden_season() -> None:
    summary = SimulationService().simulate_block(
        build_test_fc_request(), StdlibRandomSource(Seed(7))
    )

    assert summary.key_starter_outcome is None
    assert _digest(summary) == _GOLDEN_WITHOUT_SELECTION


def test_a_selection_keeps_previous_matches_and_rng_leaves_of_the_season() -> None:
    value = build_test_fc_request()
    weak = PlayerId("tfc-06")
    selection = KeyStarterSelection(FixtureId("tfc-liga-05"), date(2000, 12, 9), weak)
    rng = Seed(7)

    base = SimulationService().simulate_block(value, StdlibRandomSource(rng))
    chosen = SimulationService().simulate_block(
        replace(value, key_starter=selection), StdlibRandomSource(rng)
    )

    before = tuple(r for r in base.results if r.date < selection.date)
    assert tuple(r for r in chosen.results if r.date < selection.date) == before
    assert chosen.key_starter_outcome is not None
    assert chosen.key_starter_outcome.absence_reason is None
    assert weak in chosen.key_starter_outcome.starter_ids
    assert _digest(chosen) == _GOLDEN_WITH_SELECTION


def test_selected_player_already_required_as_youth_is_not_duplicated() -> None:
    value = request()
    youth = replace(value.managed_team.players[15], youth_minutes=True)
    players = (*value.managed_team.players[:15], youth, *value.managed_team.players[16:])
    value = replace(value, managed_team=replace(value.managed_team, players=players))

    summary = play(_with_selection(value, RESERVE))

    assert summary.key_starter_outcome is not None
    assert summary.key_starter_outcome.absence_reason is None
    assert _starters(summary).count(RESERVE) == 1


def test_youth_requirements_win_over_a_selection_that_would_exceed_eleven() -> None:
    value = request()
    youth_ids = {p.player_id for p in value.managed_team.players[:11]}
    players = tuple(
        replace(p, youth_minutes=p.player_id in youth_ids) for p in value.managed_team.players
    )
    value = replace(value, managed_team=replace(value.managed_team, players=players))

    summary = play(_with_selection(value, RESERVE))

    assert summary.key_starter_outcome is not None
    assert summary.key_starter_outcome.absence_reason == "youth_conflict"
    assert set(_starters(summary)) == youth_ids


def test_an_injury_before_the_fixture_is_a_visible_fallback() -> None:
    value = replace(
        request(),
        forced_injuries_from_effects=(ForcedInjuryDTO(RESERVE, START, 5),),
    )

    summary = play(_with_selection(value, RESERVE, LATER, END))

    assert summary.key_starter_outcome is not None
    assert summary.key_starter_outcome.absence_reason == "injured"
    assert RESERVE not in _starters(summary)
    assert len(_starters(summary)) == 11


def test_a_player_returning_on_the_fixture_date_can_start() -> None:
    value = replace(
        request(),
        forced_injuries_from_effects=(ForcedInjuryDTO(RESERVE, START, 2),),
    )

    summary = play(_with_selection(value, RESERVE, LATER, END))

    assert summary.key_starter_outcome is not None
    assert summary.key_starter_outcome.absence_reason is None


def test_a_player_sold_before_the_fixture_falls_back_without_rejecting_the_request() -> None:
    value = request()
    memberships = tuple(
        SquadMembershipInput(p.player_id, ME, None, START)
        if p.player_id == RESERVE
        else SquadMembershipInput(p.player_id, ME)
        for p in value.managed_team.players
    )
    value = replace(
        value,
        squad_memberships=memberships,
        player_pool=value.managed_team.players,
    )

    summary = play(_with_selection(value, RESERVE, LATER, END))

    assert summary.key_starter_outcome is not None
    assert summary.key_starter_outcome.absence_reason == "not_in_squad"
    assert RESERVE not in _starters(summary)


def test_a_fixture_removed_by_elimination_reports_an_empty_lineup() -> None:
    value = cup_request()
    final = FixtureId("final")
    final_day = next(f.date for f in value.season.fixtures if f.fixture_id == final)

    summary = play(_with_selection(value, RESERVE, final, final_day), OwnLoses())

    assert summary.key_starter_outcome == KeyStarterOutcome(
        final, final_day, RESERVE, (), "fixture_not_played"
    )


@pytest.mark.parametrize(
    "selection",
    [
        KeyStarterSelection(FixtureId("unknown"), START, RESERVE),
        KeyStarterSelection(KEY, END, RESERVE),
        KeyStarterSelection(KEY, START, PlayerId("nobody")),
        KeyStarterSelection(FixtureId("test-3"), date(2000, 9, 3), PlayerId("nobody")),
    ],
)
def test_invalid_selection_rejects_the_whole_request_before_randomness(
    selection: KeyStarterSelection,
) -> None:
    with pytest.raises(InvalidValueError):
        _simulate(
            replace(request(), key_starter=selection), _ExplodingRandom(Seed(1)), FixedMatches()
        )


def test_a_selection_outside_the_block_dates_is_rejected() -> None:
    value = replace(request(), end=START)

    with pytest.raises(InvalidValueError):
        play(_with_selection(value, RESERVE, LATER, END))


def test_a_selection_for_an_already_played_fixture_is_rejected() -> None:
    value = request()
    second = continuation(value, play(replace(value, end=START)))

    with pytest.raises(InvalidValueError):
        play(_with_selection(second, RESERVE))


def test_a_selection_must_be_a_typed_value() -> None:
    with pytest.raises(InvalidValueError):
        play(replace(request(), key_starter=(KEY, START, RESERVE)))  # type: ignore[arg-type]


# --------------------------------------------------------------------------- projection


def _ranked(value: BlockSimRequest, players: set[PlayerId]) -> tuple[PlayerId, ...]:
    squad = {p.player_id: p for p in _map_request(value).managed_team.squad or ()}
    return tuple(sorted(players, key=lambda pid: (-effective_rating(squad[pid]), pid.value)))


def test_projection_reuses_the_default_selector_and_ranks_the_remaining_reserves() -> None:
    value = request()

    projection = SimulationService().project_lineup(value, LATER)

    assert projection is not None
    assert set(projection.starter_ids) == _default_starters(value)
    others = {p.player_id for p in value.managed_team.players} - set(projection.starter_ids)
    assert projection.reserve_ids == _ranked(value, others)


def test_projection_breaks_equal_effective_ratings_by_player_id() -> None:
    value = request()
    projection = SimulationService().project_lineup(value, KEY)

    assert projection is not None
    squad = {p.player_id: p for p in _map_request(value).managed_team.squad or ()}
    keys = [(-effective_rating(squad[pid]), pid.value) for pid in projection.reserve_ids]
    assert keys == sorted(keys)
    assert len({k[0] for k in keys}) < len(keys)


def test_projection_follows_the_competition_priority_rotation() -> None:
    value = replace(
        request(), competition_priorities={request().season.competitions[0].competition_id: "low"}
    )
    block = _map_request(value)
    assert block.managed_team.tactic is not None
    low = select_lineup(
        block.managed_team.squad or (), block.managed_team.tactic, priority=Priority.LOW
    )

    projection = SimulationService().project_lineup(value, KEY)

    assert projection is not None
    assert projection.starter_ids == tuple(item.player.player_id for item in low.starters)


def test_projection_uses_entry_fitness_and_morale_without_simulating_earlier_matches() -> None:
    value = request()
    tired = PlayerId("test-04")
    players = tuple(
        replace(p, fitness=10, morale=0) if p.player_id == tired else p
        for p in value.managed_team.players
    )
    value = replace(value, managed_team=replace(value.managed_team, players=players))

    projection = SimulationService().project_lineup(value, LATER)

    assert projection is not None
    assert tired not in projection.starter_ids
    assert projection.reserve_ids[-1] == tired


def test_projection_excludes_known_injuries_lasting_beyond_the_fixture() -> None:
    value = request()
    players = tuple(
        replace(p, injured_until=date(2000, 9, 4)) if p.player_id == RESERVE else p
        for p in value.managed_team.players
    )
    value = replace(value, managed_team=replace(value.managed_team, players=players))

    projection = SimulationService().project_lineup(value, LATER)

    assert projection is not None
    assert RESERVE not in (*projection.starter_ids, *projection.reserve_ids)


def test_projection_includes_a_player_available_again_on_the_fixture_date() -> None:
    value = request()
    players = tuple(
        replace(p, injured_until=END) if p.player_id == RESERVE else p
        for p in value.managed_team.players
    )
    value = replace(value, managed_team=replace(value.managed_team, players=players))

    projection = SimulationService().project_lineup(value, LATER)

    assert projection is not None
    assert RESERVE in (*projection.starter_ids, *projection.reserve_ids)


def test_projection_ignores_forced_injuries_that_have_not_happened_yet() -> None:
    value = replace(request(), forced_injuries_from_effects=(ForcedInjuryDTO(RESERVE, START, 5),))

    projection = SimulationService().project_lineup(value, LATER)

    assert projection is not None
    assert RESERVE in (*projection.starter_ids, *projection.reserve_ids)


def test_projection_uses_the_squad_owned_on_the_fixture_date() -> None:
    value = request()
    newcomer = SquadPlayerInput(PlayerId("test-new"), "FW", 99)
    memberships = (
        *(
            SquadMembershipInput(p.player_id, ME, None, START)
            if p.player_id == RESERVE
            else SquadMembershipInput(p.player_id, ME)
            for p in value.managed_team.players
        ),
        SquadMembershipInput(newcomer.player_id, ME, END, None),
    )
    value = replace(
        value,
        squad_memberships=memberships,
        player_pool=(*value.managed_team.players, newcomer),
    )

    projection = SimulationService().project_lineup(value, LATER)

    assert projection is not None
    assert newcomer.player_id in projection.starter_ids
    assert RESERVE not in (*projection.starter_ids, *projection.reserve_ids)


def test_projection_without_eleven_available_players_is_absent() -> None:
    value = request()
    players = tuple(
        replace(p, injured_until=date(2000, 10, 1)) for p in value.managed_team.players[:8]
    )
    value = replace(
        value,
        managed_team=replace(
            value.managed_team, players=(*players, *value.managed_team.players[8:])
        ),
    )

    assert SimulationService().project_lineup(value, LATER) is None


@pytest.mark.parametrize("fixture", [FixtureId("unknown"), FixtureId("test-3")])
def test_projection_rejects_fixtures_outside_the_block(fixture: FixtureId) -> None:
    with pytest.raises(InvalidValueError):
        SimulationService().project_lineup(replace(request(), end=START), fixture)


def test_projection_rejects_an_already_played_fixture() -> None:
    value = request()
    second = continuation(value, play(replace(value, end=START)))

    with pytest.raises(InvalidValueError):
        SimulationService().project_lineup(second, KEY)


def test_projection_value_requires_eleven_distinct_starters_and_disjoint_reserves() -> None:
    eleven = tuple(PlayerId(f"p-{i}") for i in range(11))
    with pytest.raises(InvalidValueError):
        LineupProjectionDTO(eleven[:10], ())
    with pytest.raises(InvalidValueError):
        LineupProjectionDTO(eleven, (eleven[0],))
    with pytest.raises(InvalidValueError):
        LineupProjectionDTO(eleven, (PlayerId("r"), PlayerId("r")))
    assert LineupProjectionDTO(eleven, (PlayerId("r"),)).reserve_ids == (PlayerId("r"),)
