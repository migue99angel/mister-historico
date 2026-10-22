"""Reads a content directory: YAML parsing and schema validation, accumulating issues."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from pydantic import ValidationError

from mister.catalog.infrastructure.content_schema.base import ContentModel
from mister.catalog.infrastructure.content_schema.club import ClubFile
from mister.catalog.infrastructure.content_schema.dilemmas import DilemmasFile
from mister.catalog.infrastructure.content_schema.fixtures import FixturesFile
from mister.catalog.infrastructure.content_schema.issues import IssueSink
from mister.catalog.infrastructure.content_schema.season import SeasonFile
from mister.catalog.infrastructure.content_schema.squad import AggregateFile, SquadFile
from mister.catalog.infrastructure.content_schema.standings import StandingsFile
from mister.catalog.infrastructure.content_schema.texts import TextsFile
from mister.catalog.infrastructure.content_schema.tree import ContentTree, SeasonContent


class _DuplicateKeyError(Exception):
    def __init__(self, key: object) -> None:
        super().__init__(f"duplicate key {key!r}")
        self.key = str(key)


class _UniqueKeyLoader(yaml.SafeLoader):  # type: ignore[misc]
    """A safe loader that refuses duplicate mapping keys instead of silently keeping the last."""

    def construct_mapping(self, node: Any, deep: bool = False) -> dict[Any, Any]:
        seen: set[Any] = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=True)
            if key in seen:
                raise _DuplicateKeyError(key)
            seen.add(key)
        mapping: dict[Any, Any] = super().construct_mapping(node, deep=deep)
        return mapping


@dataclass
class ReadResult:
    """The valid part of the tree plus the identifiers of the files that failed to load."""

    tree: ContentTree
    failed_club_seasons: set[str] = field(default_factory=set)
    failed_seasons: set[str] = field(default_factory=set)


def _field_name(location: tuple[int | str, ...]) -> str:
    return ".".join(str(part) for part in location)


def _load_model[M: ContentModel](
    root: Path, path: Path, model: type[M], sink: IssueSink
) -> M | None:
    relative = path.relative_to(root).as_posix()
    if not path.is_file():
        sink.add(relative, "", "file is missing")
        return None
    try:
        data = yaml.load(path.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader)  # noqa: S506
    except _DuplicateKeyError as error:
        sink.add(relative, error.key, "duplicate key in YAML mapping")
        return None
    except yaml.YAMLError as error:
        sink.add(relative, "", f"invalid YAML: {str(error).splitlines()[0]}")
        return None
    try:
        return model.model_validate(data)
    except ValidationError as error:
        for detail in error.errors():
            message = detail["msg"].removeprefix("Value error, ")
            sink.add(relative, _field_name(detail["loc"]), message)
        return None


def _read_clubs(root: Path, result: ReadResult, sink: IssueSink) -> None:
    for path in sorted((root / "clubs").glob("*.yaml")):
        club = _load_model(root, path, ClubFile, sink)
        if club is None:
            continue
        if club.club_id != path.stem:
            sink.add(
                path.relative_to(root).as_posix(), "club_id", f"must match file name {path.stem!r}"
            )
        result.tree.clubs[path.stem] = club


def _read_club_season(root: Path, directory: Path, result: ReadResult, sink: IssueSink) -> None:
    name = directory.name
    squad_path, aggregate_path = directory / "squad.yaml", directory / "aggregate.yaml"
    if squad_path.is_file() == aggregate_path.is_file():
        sink.add(
            directory.relative_to(root).as_posix(),
            "",
            "needs exactly one of squad.yaml or aggregate.yaml",
        )
        result.failed_club_seasons.add(name)
        return
    if squad_path.is_file():
        squad = _load_model(root, squad_path, SquadFile, sink)
        loaded: SquadFile | AggregateFile | None = squad
        if squad is not None:
            result.tree.squads[name] = squad
        path = squad_path
    else:
        aggregate = _load_model(root, aggregate_path, AggregateFile, sink)
        loaded = aggregate
        if aggregate is not None:
            result.tree.aggregates[name] = aggregate
        path = aggregate_path
    if loaded is None:
        result.failed_club_seasons.add(name)
    elif loaded.club_season != name:
        sink.add(path.relative_to(root).as_posix(), "club_season", f"must match directory {name!r}")
        result.tree.squads.pop(name, None)
        result.tree.aggregates.pop(name, None)
        result.failed_club_seasons.add(name)


def _read_season(root: Path, directory: Path, result: ReadResult, sink: IssueSink) -> None:
    season = _load_model(root, directory / "season.yaml", SeasonFile, sink)
    fixtures = _load_model(root, directory / "fixtures.yaml", FixturesFile, sink)
    standings = _load_model(root, directory / "standings.yaml", StandingsFile, sink)
    dilemmas = _load_model(root, directory / "dilemmas.yaml", DilemmasFile, sink)
    texts = _load_model(root, directory / "texts.yaml", TextsFile, sink)
    if season is None or fixtures is None or standings is None or dilemmas is None or texts is None:
        result.failed_seasons.add(directory.name)
        return
    if season.slug != directory.name:
        sink.add(
            f"{directory.relative_to(root).as_posix()}/season.yaml",
            "slug",
            f"must match directory {directory.name!r}",
        )
        result.failed_seasons.add(directory.name)
        return
    result.tree.seasons[directory.name] = SeasonContent(
        season, fixtures, standings, dilemmas, texts
    )


def read_tree(root: Path, sink: IssueSink) -> ReadResult:
    """Parse and schema-validate every file under `root`, reporting all problems."""
    result = ReadResult(ContentTree())
    if not root.is_dir():
        sink.add(".", "", f"content root {root} does not exist")
        return result
    _read_clubs(root, result, sink)
    for directory in sorted(p for p in (root / "club-seasons").glob("*") if p.is_dir()):
        _read_club_season(root, directory, result, sink)
    for directory in sorted(p for p in (root / "seasons").glob("*") if p.is_dir()):
        _read_season(root, directory, result, sink)
    return result
