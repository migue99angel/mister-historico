"""Fixture-date squad selection retains all players' physical state."""

from dataclasses import replace
from datetime import date

import pytest
from tests.simulation.unit.test_simulate_block import (
    END,
    ME,
    START,
    FixedMatches,
    play,
    request,
)

from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import ClubSeasonId, PlayerId
from mister.simulation.application.api import (
    ForcedInjuryDTO,
    SquadMembershipInput,
    SquadTeamInput,
    TacticDTO,
)
from mister.simulation.application.simulate_block import _map_request
from mister.simulation.domain.dated_squads import DatedMembership, owner_on


def test_membership_join_and_leave_dates_are_inclusive() -> None:
    player = PlayerId("dated-player")
    membership = DatedMembership(player, ME, START, END)

    assert owner_on((membership,), player, START) == ME
    assert owner_on((membership,), player, date(2000, 9, 2)) == ME
    assert owner_on((membership,), player, END) == ME
    assert owner_on((membership,), player, date(2000, 8, 31)) is None
    assert owner_on((membership,), player, date(2000, 9, 4)) is None


def test_membership_bounds_are_inclusive_on_both_fixture_dates() -> None:
    value = request()
    memberships = tuple(
        SquadMembershipInput(player.player_id, ME, START, END)
        for player in value.managed_team.players
    )
    value = replace(value, squad_memberships=memberships, player_pool=value.managed_team.players)
    spy = FixedMatches()

    summary = play(value, spy)

    assert summary.block_id == value.block_id
    assert len(spy.setups) == 2
    summary_states = {item.player_id for item in play(value).player_states}
    assert summary_states == {player.player_id for player in value.managed_team.players}


def test_effective_transfer_date_selects_the_player_for_destination_fixture() -> None:
    value = request()
    player = value.managed_team.players[0]
    rival_id = ClubSeasonId("sample-united-2000-01")
    rival = SquadTeamInput(
        rival_id,
        tuple(
            replace(item, player_id=PlayerId(f"rival-{index:02}"))
            for index, item in enumerate(value.managed_team.players)
        ),
        TacticDTO("balanced", "4-4-2"),
    )
    own_intervals = tuple(
        SquadMembershipInput(item.player_id, ME, None, date(2000, 8, 31))
        if item.player_id == player.player_id
        else SquadMembershipInput(item.player_id, ME)
        for item in value.managed_team.players
    )
    rival_intervals = tuple(
        SquadMembershipInput(item.player_id, rival_id) for item in rival.players
    )
    memberships = (
        *own_intervals,
        *rival_intervals,
        SquadMembershipInput(player.player_id, rival_id, START, None),
    )
    pool = (*value.managed_team.players, *rival.players)
    value = replace(
        value,
        season=replace(value.season, teams=(value.season.teams[0], rival)),
        squad_memberships=memberships,
        player_pool=pool,
    )

    summary = play(value)

    moved_state = next(item for item in summary.player_states if item.player_id == player.player_id)
    assert moved_state.minutes_played == 0
    assert moved_state.fitness == player.fitness
    assert moved_state.player_id in {item.player_id for item in summary.player_states}


def test_dated_memberships_reject_overlapping_player_clubs() -> None:
    value = request()
    player = value.managed_team.players[0]
    memberships = (
        SquadMembershipInput(player.player_id, ME, START, END),
        SquadMembershipInput(player.player_id, ClubSeasonId("sample-united-2000-01"), END, None),
    )
    with pytest.raises(InvalidValueError):
        _map_request(
            replace(value, squad_memberships=memberships, player_pool=value.managed_team.players)
        )


def test_future_forced_injury_applies_to_a_player_in_the_pool() -> None:
    value = request()
    memberships = tuple(
        SquadMembershipInput(player.player_id, ME, START, END)
        for player in value.managed_team.players
    )
    target = value.managed_team.players[0]
    value = replace(
        value,
        squad_memberships=memberships,
        player_pool=value.managed_team.players,
        forced_injuries_from_effects=(ForcedInjuryDTO(target.player_id, date(2000, 9, 2), 5),),
    )

    summary = play(value)

    injured = next(item for item in summary.player_states if item.player_id == target.player_id)
    assert injured.injured_until == date(2000, 9, 7)


def test_future_forced_injury_for_a_rival_player_survives_until_he_joins() -> None:
    value = request()
    target = value.managed_team.players[0]
    rival_id = ClubSeasonId("sample-united-2000-01")
    rival = SquadTeamInput(
        rival_id,
        tuple(
            replace(item, player_id=PlayerId(f"rival-{index:02}"))
            for index, item in enumerate(value.managed_team.players)
        ),
        TacticDTO("balanced", "4-4-2"),
    )
    memberships = [
        SquadMembershipInput(player.player_id, ME, START, END)
        for player in value.managed_team.players
        if player.player_id != target.player_id
    ]
    memberships.extend(SquadMembershipInput(player.player_id, rival_id) for player in rival.players)
    memberships.extend(
        (
            SquadMembershipInput(target.player_id, rival_id, None, START),
            SquadMembershipInput(target.player_id, ME, date(2000, 9, 2), None),
        )
    )
    value = replace(
        value,
        season=replace(value.season, teams=(value.season.teams[0], rival)),
        squad_memberships=tuple(memberships),
        player_pool=(*value.managed_team.players, *rival.players),
        forced_injuries_from_effects=(ForcedInjuryDTO(target.player_id, date(2000, 9, 2), 5),),
    )

    summary = play(value)

    injury = next(item for item in summary.injuries if item.player_id == target.player_id)
    state = next(item for item in summary.player_states if item.player_id == target.player_id)
    assert injury.forced is True
    assert state.injured_until == date(2000, 9, 7)


def test_youth_player_transferred_into_managed_squad_gets_a_later_opportunity() -> None:
    value = request()
    youth = value.managed_team.players[0]
    rival_id = ClubSeasonId("sample-united-2000-01")
    rival = SquadTeamInput(
        rival_id,
        tuple(
            replace(item, player_id=PlayerId(f"rival-{index:02}"))
            for index, item in enumerate(value.managed_team.players)
        ),
        TacticDTO("balanced", "4-4-2"),
    )
    pool = tuple(
        replace(item, youth_minutes=True) if item.player_id == youth.player_id else item
        for item in (*value.managed_team.players, *rival.players)
    )
    memberships = [
        SquadMembershipInput(item.player_id, ME, START, END)
        for item in value.managed_team.players
        if item.player_id != youth.player_id
    ]
    memberships.append(SquadMembershipInput(youth.player_id, rival_id, None, START))
    memberships.extend(SquadMembershipInput(item.player_id, rival_id) for item in rival.players)
    memberships.append(SquadMembershipInput(youth.player_id, ME, date(2000, 9, 2), None))
    value = replace(
        value,
        season=replace(value.season, teams=(value.season.teams[0], rival)),
        squad_memberships=tuple(memberships),
        player_pool=pool,
    )

    summary = play(value)

    state = next(item for item in summary.player_states if item.player_id == youth.player_id)
    assert state.minutes_played > 0


def test_all_player_states_continue_across_split_blocks() -> None:
    value = request()
    memberships = tuple(
        SquadMembershipInput(player.player_id, ME, START, END)
        for player in value.managed_team.players
    )
    dated = replace(value, squad_memberships=memberships, player_pool=value.managed_team.players)
    first = play(replace(dated, end=START))
    states = {state.player_id: state for state in first.player_states}
    second = replace(
        dated,
        start=date(2000, 9, 2),
        state_as_of=START,
        prior_results=first.results,
        player_pool=tuple(
            replace(
                player,
                fitness=states[player.player_id].fitness,
                injured_until=states[player.player_id].injured_until,
            )
            for player in dated.player_pool or ()
        ),
    )

    split = play(second)
    whole = play(dated)

    assert tuple(
        (state.player_id, state.fitness, state.injured_until) for state in split.player_states
    ) == tuple(
        (state.player_id, state.fitness, state.injured_until) for state in whole.player_states
    )


def test_empty_dated_inputs_do_not_fall_back_to_the_legacy_squad() -> None:
    value = replace(request(), squad_memberships=(), player_pool=())

    with pytest.raises(InvalidValueError):
        play(value)


def test_partial_dated_inputs_are_rejected() -> None:
    with pytest.raises(InvalidValueError):
        _map_request(replace(request(), squad_memberships=()))


def test_membership_rejects_an_unknown_club_reference() -> None:
    value = request()
    membership = SquadMembershipInput(
        value.managed_team.players[0].player_id,
        ClubSeasonId("unknown-club-2000-01"),
    )
    with pytest.raises(InvalidValueError):
        _map_request(
            replace(value, squad_memberships=(membership,), player_pool=value.managed_team.players)
        )


def test_membership_rejects_a_player_missing_from_the_pool() -> None:
    value = request()
    membership = SquadMembershipInput(value.managed_team.players[0].player_id, ME)
    with pytest.raises(InvalidValueError):
        _map_request(replace(value, squad_memberships=(membership,), player_pool=()))
