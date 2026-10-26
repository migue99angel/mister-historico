"""Malformed external DTOs fail deterministically without changing caller-owned state."""

from copy import deepcopy
from dataclasses import replace
from datetime import datetime
from types import SimpleNamespace
from typing import Any

import pytest
from tests.simulation.unit.test_season_competitions import CUP, OwnWins, cup_request, group_request
from tests.simulation.unit.test_simulate_block import ME, RIVAL, FixedMatches, play, request

from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import ClubSeasonId, CompetitionId, PlayerId
from mister.simulation.application import api
from mister.simulation.domain.model import MatchResult, MatchSetup, Score

_BASE = request()
_GROUP = group_request()
_CUP = cup_request()


def changed(value: Any, **fields: Any) -> Any:
    """Deliberately bypass static DTO annotations, as malformed boundary values do."""
    return replace(value, **fields)


def fixture(**fields: Any) -> api.BlockSimRequest:
    first = changed(_BASE.season.fixtures[0], **fields)
    return replace(
        _BASE, season=replace(_BASE.season, fixtures=(first, *_BASE.season.fixtures[1:]))
    )


def competition(**fields: Any) -> api.BlockSimRequest:
    return replace(
        _BASE,
        season=replace(
            _BASE.season, competitions=(changed(_BASE.season.competitions[0], **fields),)
        ),
    )


def squad_player(**fields: Any) -> api.BlockSimRequest:
    original = _BASE.managed_team
    player = changed(original.players[0], **fields)
    return replace(_BASE, managed_team=replace(original, players=(player, *original.players[1:])))


def group_stage(**fields: Any) -> api.BlockSimRequest:
    original = _GROUP.season.competitions[0]
    stage = changed(original.stages[0], **fields)
    return replace(
        _GROUP,
        season=replace(
            _GROUP.season, competitions=(replace(original, stages=(stage, original.stages[1])),)
        ),
    )


def cup_slot(**fields: Any) -> api.BlockSimRequest:
    declaration = (_CUP.season.knockout_calendar or ())[0]
    slots = declaration.slots or ()
    return replace(
        _CUP,
        season=replace(
            _CUP.season,
            knockout_calendar=(
                replace(declaration, slots=(changed(slots[0], **fields), *slots[1:])),
            ),
        ),
    )


@pytest.mark.parametrize(
    "value",
    [
        pytest.param(changed(_BASE, block_id="block"), id="untyped-block-id"),
        pytest.param(
            changed(_BASE, start=datetime(2000, 9, 1)), id="timestamp-is-not-calendar-date"
        ),
        pytest.param(
            replace(_BASE, managed_team=replace(_BASE.managed_team, club_season_id=RIVAL)),
            id="wrong-managed-club",
        ),
        pytest.param(
            replace(_BASE, season=replace(_BASE.season, teams=_BASE.season.teams[1:])),
            id="missing-original-managed-reference",
        ),
        pytest.param(
            replace(_BASE, team_overrides=(_BASE.managed_team,)),
            id="override-cannot-replace-managed-club",
        ),
        pytest.param(
            replace(
                _BASE,
                forced_injuries_from_effects=(
                    api.ForcedInjuryDTO(PlayerId("unknown"), _BASE.start, 1),
                ),
            ),
            id="injury-outside-squad",
        ),
        pytest.param(squad_player(player_id="player"), id="untyped-player-id"),
        pytest.param(squad_player(youth_minutes=1), id="integer-is-not-youth-flag"),
        pytest.param(
            replace(
                _BASE,
                season=replace(
                    _BASE.season,
                    teams=(
                        _BASE.managed_team,
                        changed(_BASE.season.teams[1], club_season_id="rival"),
                    ),
                ),
            ),
            id="untyped-reference-club",
        ),
        pytest.param(
            changed(
                _BASE,
                season=changed(
                    _BASE.season, teams=(_BASE.managed_team, SimpleNamespace(club_season_id=RIVAL))
                ),
            ),
            id="unsupported-team-shape",
        ),
        pytest.param(competition(rounds=0), id="invalid-round-repetitions"),
        pytest.param(competition(kind="friendly"), id="unsupported-competition-kind"),
        pytest.param(competition(points_per_win=None), id="missing-league-scoring-rule"),
        pytest.param(
            competition(participants=(ME, ClubSeasonId("unknown-2000-01"))),
            id="unknown-participant",
        ),
        pytest.param(fixture(fixture_id="fixture"), id="untyped-fixture-id"),
        pytest.param(fixture(home="club"), id="untyped-fixture-side"),
        pytest.param(fixture(round=0), id="nonpositive-matchday"),
        pytest.param(fixture(key=1), id="integer-is-not-key-flag"),
        pytest.param(
            fixture(competition_id=CompetitionId("unknown")), id="fixture-outside-competition"
        ),
        pytest.param(fixture(stage_id="groups", group_id="a"), id="league-cannot-be-group-stage"),
        pytest.param(
            changed(_BASE, season=changed(_BASE.season, fixtures=(SimpleNamespace(),))),
            id="unsupported-fixture-shape",
        ),
        pytest.param(
            replace(
                _BASE,
                season=replace(
                    _BASE.season,
                    historical_standings=(
                        replace(_BASE.season.historical_standings[0], competition_id=CUP),
                    ),
                ),
            ),
            id="snapshot-unknown-competition",
        ),
        pytest.param(
            replace(
                _BASE,
                season=replace(
                    _BASE.season,
                    historical_standings=(
                        replace(
                            _BASE.season.historical_standings[0], stage_id="groups", group_id="a"
                        ),
                    ),
                ),
            ),
            id="league-snapshot-scope",
        ),
        pytest.param(
            replace(
                _BASE,
                season=replace(
                    _BASE.season,
                    historical_standings=(
                        replace(
                            _BASE.season.historical_standings[0],
                            rows=tuple(
                                replace(row, position=1)
                                for row in _BASE.season.historical_standings[0].rows
                            ),
                        ),
                    ),
                ),
            ),
            id="snapshot-duplicate-positions",
        ),
        pytest.param(
            replace(
                _BASE,
                season=replace(
                    _BASE.season,
                    historical_standings=(
                        replace(
                            _BASE.season.historical_standings[0],
                            rows=(
                                replace(_BASE.season.historical_standings[0].rows[0], points=99),
                                _BASE.season.historical_standings[0].rows[1],
                            ),
                        ),
                    ),
                ),
            ),
            id="snapshot-inconsistent-points",
        ),
        pytest.param(group_stage(stage_id=""), id="empty-stage-id"),
        pytest.param(group_stage(points_per_win=None), id="group-missing-scoring-rule"),
        pytest.param(
            group_stage(tiebreakers=("head_to_head_points",), reapply_head_to_head=None),
            id="unknown-mini-table-reapplication",
        ),
        pytest.param(
            group_stage(groups=(api.GroupInput("a", (ME, RIVAL)),)), id="group-needs-four-clubs"
        ),
        pytest.param(group_stage(round="final"), id="knockout-stage-cannot-contain-groups"),
        pytest.param(
            replace(
                _CUP,
                season=replace(
                    _CUP.season, competitions=(replace(_CUP.season.competitions[0], stages=()),)
                ),
            ),
            id="cup-needs-stages",
        ),
        pytest.param(cup_slot(date=None), id="unknown-slot-date"),
        pytest.param(cup_slot(venue=None), id="unknown-slot-venue"),
        pytest.param(cup_slot(sources=()), id="slot-needs-sources"),
        pytest.param(
            cup_slot(home=ClubSeasonId("unknown-2000-01")), id="slot-outside-participants"
        ),
        pytest.param(cup_slot(date=_CUP.end), id="slot-contradicts-managed-calendar"),
        pytest.param(
            replace(
                _CUP,
                season=replace(
                    _CUP.season, competitions=(replace(_CUP.season.competitions[0], real_ties=()),)
                ),
            ),
            id="knockout-needs-historical-ties",
        ),
        pytest.param(
            replace(
                _CUP,
                season=replace(
                    _CUP.season,
                    competitions=(
                        replace(
                            _CUP.season.competitions[0],
                            real_ties=tuple(
                                replace(tie, winner=None) if tie.stage_id == "semi" else tie
                                for tie in _CUP.season.competitions[0].real_ties
                            ),
                        ),
                    ),
                ),
            ),
            id="next-stage-needs-unique-known-feeder",
        ),
    ],
)
def test_invalid_block_input_fails_with_domain_error_without_mutating_it(
    value: api.BlockSimRequest,
) -> None:
    before = deepcopy(value)
    for _ in range(2):
        with pytest.raises(InvalidValueError):
            play(value, OwnWins())
        assert value == before


def test_league_strategy_cannot_return_extra_time() -> None:
    class DecidingPeriods(FixedMatches):
        def simulate(
            self, setup: MatchSetup, rng: object, *, decisive: bool = False
        ) -> MatchResult:
            return MatchResult(Score(1, 0), Score(0, 0))

    value = request()
    before = deepcopy(value)
    with pytest.raises(InvalidValueError, match="deciding periods"):
        play(value, DecidingPeriods())
    assert value == before


def test_missing_historical_managed_score_is_not_replaced_with_zero_goals() -> None:
    value = fixture(real_result=None)
    with pytest.raises(InvalidValueError, match="historical score"):
        play(value)
