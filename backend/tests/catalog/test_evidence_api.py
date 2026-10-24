"""Compatible published evidence DTOs owned independently by both contexts."""

from dataclasses import FrozenInstanceError, fields
from datetime import date

import pytest
from tests.contracts.suites.sample_content import make_sample_season

from mister.catalog.application import api as catalog
from mister.shared_kernel.ids import ClubSeasonId, CompetitionId, FixtureId
from mister.simulation.application import api as simulation


@pytest.mark.parametrize("kind", [catalog.StageDTO, simulation.StageInput])
def test_stage_variant_is_appended_optional_and_keeps_legacy_construction(kind: type) -> None:
    assert fields(kind)[-1].name == "away_goals_in_extra_time"
    assert fields(kind)[-1].default is None


def test_existing_season_constructors_leave_evidence_unknown() -> None:
    assert make_sample_season().head_to_head is None
    assert (
        simulation.SeasonSimInput(ClubSeasonId("test-fc-2000-01"), (), (), ()).head_to_head is None
    )


def test_both_contexts_publish_the_same_independent_evidence_shape() -> None:
    names = ("HeadToHeadFixture", "HeadToHeadResult", "HeadToHeadEvidence")
    for name in names:
        left = getattr(catalog, name + "DTO")
        right = getattr(simulation, name + "Input")
        assert left is not right
        assert [f.name for f in fields(left)] == [f.name for f in fields(right)]
        assert left.__module__ == catalog.__name__
        assert right.__module__ == simulation.__name__


def test_empty_known_evidence_preserves_coverage_and_editorial_provenance() -> None:
    evidence = catalog.HeadToHeadEvidenceDTO(
        CompetitionId("liga-test"),
        date(2000, 9, 1),
        (ClubSeasonId("test-fc-2000-01"), ClubSeasonId("sample-united-2000-01")),
        (),
        (),
        ("https://example.org/test-content/evidence",),
        "ok",
    )
    assert evidence.schedule == ()
    assert evidence.results == ()
    assert evidence.verify == "ok"
    assert evidence.sources
    with pytest.raises(FrozenInstanceError):
        evidence.verify = "pending"  # type: ignore[misc]


def test_pending_result_can_travel_without_fabricating_a_score() -> None:
    result = simulation.HeadToHeadResultInput(FixtureId("test-match"), None, (), "pending")
    assert result.score is None
