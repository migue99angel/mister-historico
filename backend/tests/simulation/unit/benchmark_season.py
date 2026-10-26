"""Reproducible full Test FC benchmark; YAML loading is outside the timed engine calls.

Run from backend with PYTHONPATH=src python -m tests.simulation.unit.benchmark_season.
"""

import json
import math
from pathlib import Path
from statistics import median
from time import perf_counter
from typing import Any

import yaml

from mister.shared_kernel.ids import BlockId, ClubSeasonId, CompetitionId, FixtureId, PlayerId
from mister.shared_kernel.randomness import StdlibRandomSource
from mister.shared_kernel.seed import Seed
from mister.simulation.application import api

_ROOT = Path(__file__).parents[2] / "fixtures" / "content"
_BUDGET_MS = 20.0


def _load(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text())
    assert isinstance(value, dict)
    return value


def _stage(value: dict[str, Any]) -> api.StageInput:
    variant = value.get("away_goals_in_extra_time")
    reapply = value.get("reapply_head_to_head")
    return api.StageInput(
        value["id"],
        value["round"],
        value["legs"],
        value["away_goals_rule"],
        value["extra_time"],
        value["penalties"],
        tuple(
            api.GroupInput(g["id"], tuple(ClubSeasonId(c) for c in g["participants"]))
            for g in value.get("groups", ())
        ),
        value.get("points_per_win"),
        value.get("points_per_draw"),
        tuple(value.get("tiebreakers", ())),
        value.get("advance_per_group"),
        variant["value"] if isinstance(variant, dict) else variant,
        reapply["value"] if isinstance(reapply, dict) else reapply,
    )


def build_test_fc_request() -> api.BlockSimRequest:
    season = _load(_ROOT / "seasons" / "test-fc-2000-01" / "season.yaml")
    tables = _load(_ROOT / "seasons" / "test-fc-2000-01" / "standings.yaml")
    calendar = _load(_ROOT / "seasons" / "test-fc-2000-01" / "fixtures.yaml")
    managed = ClubSeasonId(season["club_season"])
    competitions = []
    teams: list[api.TeamInput] = []
    tactics = api.TacticDTO("balanced", "4-4-2")
    for club in sorted({c for comp in season["competitions"] for c in comp["participants"]}):
        folder = _ROOT / "club-seasons" / club
        if (folder / "squad.yaml").exists():
            squad = _load(folder / "squad.yaml")
            teams.append(
                api.SquadTeamInput(
                    ClubSeasonId(club),
                    tuple(
                        api.SquadPlayerInput(
                            PlayerId(p["player_id"]), p["position"], p["rating"], p.get("age")
                        )
                        for p in squad["players"]
                    ),
                    tactics,
                )
            )
        else:
            aggregate = _load(folder / "aggregate.yaml")
            teams.append(
                api.AggregateTeamInput(
                    ClubSeasonId(club), aggregate["attack"], aggregate["defense"]
                )
            )
    for competition in season["competitions"]:
        stats = competition.get("league_stats", competition.get("goal_baseline"))
        if "from_league" in stats:
            stats = next(
                c["league_stats"] for c in season["competitions"] if c["id"] == stats["from_league"]
            )
        competitions.append(
            api.CompetitionInput(
                CompetitionId(competition["id"]),
                competition["kind"],
                competition["tier"],
                tuple(ClubSeasonId(c) for c in competition["participants"]),
                (stats["home_goals"] + stats["away_goals"]) / (2 * stats["matches"]),
                math.sqrt(stats["home_goals"] / stats["away_goals"]),
                competition.get("rounds"),
                competition.get("points_per_win"),
                competition.get("points_per_draw"),
                tuple(competition.get("tiebreakers", ())),
                tuple(_stage(s) for s in competition.get("stages", ())),
                tuple(
                    api.RealTieInput(
                        t["stage"],
                        (ClubSeasonId(t["clubs"][0]), ClubSeasonId(t["clubs"][1])),
                        ClubSeasonId(t["winner"]) if t.get("winner") else None,
                    )
                    for t in tables["ties"]
                    if t["competition"] == competition["id"]
                ),
            )
        )
    fixtures = []
    for fixture in calendar["fixtures"]:
        opponent = ClubSeasonId(fixture["opponent"])
        home, away = (opponent, managed) if fixture["venue"] == "away" else (managed, opponent)
        result = fixture["result"]
        fixtures.append(
            api.FixtureInput(
                FixtureId(fixture["id"]),
                fixture["date"],
                CompetitionId(fixture["competition"]),
                home,
                away,
                "neutral" if fixture["venue"] == "neutral" else "home",
                fixture.get("key", False),
                fixture.get("round"),
                fixture.get("leg"),
                fixture.get("stage"),
                fixture.get("group"),
                api.RealResultInput(
                    result["goals_for"],
                    result["goals_against"],
                    result.get("extra_time", False),
                    result.get("penalties_for"),
                    result.get("penalties_against"),
                ),
            )
        )
    evidence = tuple(
        api.HeadToHeadEvidenceInput(
            CompetitionId(e["competition"]),
            e["complete_through"],
            tuple(ClubSeasonId(c) for c in e["covered_clubs"]),
            tuple(
                api.HeadToHeadFixtureInput(
                    FixtureId(f["fixture_id"]),
                    f["date"],
                    ClubSeasonId(f["home"]),
                    ClubSeasonId(f["away"]),
                    tuple(f["sources"]),
                    f["verify"],
                    f.get("venue"),
                )
                for f in e["schedule"]
            ),
            tuple(
                api.HeadToHeadResultInput(
                    FixtureId(r["fixture_id"]),
                    tuple(r["score"]) if r["score"] is not None else None,
                    tuple(r["sources"]),
                    r["verify"],
                )
                for r in e["results"]
            ),
            tuple(e["sources"]),
            e["verify"],
            e.get("stage"),
            e.get("group"),
        )
        for e in tables["head_to_head"]
    )
    slots = tuple(
        api.KnockoutCalendarInput(
            CompetitionId(c["competition"]),
            tuple(
                api.KnockoutSlotInput(
                    FixtureId(s["fixture_id"]),
                    s["stage_id"],
                    s["date"],
                    ClubSeasonId(s["home"]),
                    ClubSeasonId(s["away"]),
                    s["venue"],
                    s["leg"],
                    tuple(s["sources"]),
                    s["verify"],
                )
                for s in c["slots"]
            ),
            tuple(c["sources"]),
            c["verify"],
        )
        for c in tables["knockout_calendar"]
    )
    entries = tuple(
        api.GroupEntryAssignmentsInput(
            CompetitionId(c["competition"]),
            tuple(
                api.GroupEntryAssignmentInput(
                    e["source_stage_id"],
                    e["group_id"],
                    e["qualifying_position"],
                    e["target_stage_id"],
                    ClubSeasonId(e["historical_representative"]),
                    tuple(e["sources"]),
                    e["verify"],
                )
                for e in c["entries"]
            ),
            tuple(c["sources"]),
            c["verify"],
        )
        for c in tables["group_entry_assignments"]
    )
    snapshots = tuple(
        api.StandingsDTO(
            CompetitionId(t["competition"]),
            t["date"],
            tuple(
                api.StandingRowDTO(
                    ClubSeasonId(r["club_season"]),
                    r["position"],
                    r["played"],
                    r["won"],
                    r["drawn"],
                    r["lost"],
                    r["goals_for"],
                    r["goals_against"],
                    r["points"],
                )
                for r in t["table"]
            ),
            t.get("stage"),
            t.get("group"),
        )
        for t in tables["cutoffs"]
    )
    injuries = tuple(
        api.ForcedInjuryDTO(PlayerId(i["player_id"]), i["date"], i["days"])
        for i in season["forced_events"]
        if i["type"] == "injury"
    )
    content = api.SeasonSimInput(
        managed,
        tuple(teams),
        tuple(competitions),
        tuple(fixtures),
        injuries,
        snapshots,
        evidence,
        slots,
        entries,
    )
    own = next(t for t in teams if t.club_season_id == managed)
    assert isinstance(own, api.SquadTeamInput)
    return api.BlockSimRequest(
        content,
        BlockId("test-full-season"),
        season["blocks"][0]["start"],
        season["blocks"][-1]["end"],
        own,
    )


def main() -> None:
    value = build_test_fc_request()
    service = api.SimulationService()

    def run() -> api.BlockSummaryDTO:
        return service.simulate_block(value, StdlibRandomSource(Seed(20261026)))

    summary = run()
    samples = []
    for _ in range(7):
        start = perf_counter()
        for _ in range(20):
            run()
        samples.append((perf_counter() - start) * 1000 / 20)
    report = {
        "seed": 20261026,
        "matches": len(summary.results),
        "samples_ms": samples,
        "median_ms": median(samples),
        "budget_ms": _BUDGET_MS,
    }
    print(json.dumps(report, indent=2))  # noqa: T201 - standalone benchmark
    if median(samples) >= _BUDGET_MS:
        raise SystemExit("Full Test FC season exceeds the 20 ms budget")


if __name__ == "__main__":
    main()
