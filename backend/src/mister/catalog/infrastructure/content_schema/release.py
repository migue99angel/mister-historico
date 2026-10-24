"""Release-mode rules: nothing pending and nothing in draft may ship."""

from pydantic import BaseModel

from mister.catalog.infrastructure.content_schema.context import SeasonContext
from mister.catalog.infrastructure.content_schema.evidence_checks import check_release_evidence
from mister.catalog.infrastructure.content_schema.issues import IssueSink
from mister.catalog.infrastructure.content_schema.season import LeagueCompetition
from mister.catalog.infrastructure.content_schema.tree import ContentTree


def _walk_pending(value: object, path: str, parts: list[str], sink: IssueSink) -> None:
    if isinstance(value, BaseModel):
        if getattr(value, "verify", None) == "pending":
            sink.add(
                path, ".".join([*parts, "verify"]), "verify: pending is not allowed in release mode"
            )
        for name in type(value).model_fields:
            _walk_pending(getattr(value, name), path, [*parts, name], sink)
    elif isinstance(value, tuple):
        for index, item in enumerate(value):
            _walk_pending(item, path, [*parts, str(index)], sink)


def check_release(tree: ContentTree, sink: IssueSink) -> None:
    """Report every `verify: pending` datum and every `draft` text."""
    for slug, squad in tree.squads.items():
        _walk_pending(squad, f"club-seasons/{slug}/squad.yaml", [], sink)
    for slug, aggregate in tree.aggregates.items():
        _walk_pending(aggregate, f"club-seasons/{slug}/aggregate.yaml", [], sink)
    for slug, content in tree.seasons.items():
        check_release_evidence(SeasonContext(tree, frozenset(), slug, sink))
        for ci, competition in enumerate(content.season.competitions):
            if isinstance(competition, LeagueCompetition):
                continue
            for si, stage in enumerate(competition.stages):
                if stage.legs == 2 and stage.away_goals_rule and stage.extra_time and (
                    stage.away_goals_in_extra_time is None
                    or stage.away_goals_in_extra_time.value is None
                    or stage.away_goals_in_extra_time.verify != "ok"
                ):
                    sink.add(f"seasons/{slug}/season.yaml",
                             f"competitions.{ci}.stages.{si}.away_goals_in_extra_time",
                             "an explicit verified extra-time away-goals rule is required")
        base = f"seasons/{slug}"
        _walk_pending(content.season, f"{base}/season.yaml", [], sink)
        _walk_pending(content.fixtures, f"{base}/fixtures.yaml", [], sink)
        _walk_pending(content.standings, f"{base}/standings.yaml", [], sink)
        _walk_pending(content.dilemmas, f"{base}/dilemmas.yaml", [], sink)
        for index, text in enumerate(content.texts.texts):
            if text.status == "draft":
                sink.add(
                    f"{base}/texts.yaml",
                    f"texts.{index}.status",
                    "draft texts are not allowed in release mode",
                )
