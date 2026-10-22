"""`load_content_tree`: read, validate and cross-check a whole `content/` directory."""

from pathlib import Path

from mister.catalog.infrastructure.content_schema.integrity import (
    check_club_references,
    check_players_across_squads,
)
from mister.catalog.infrastructure.content_schema.issues import ContentValidationError, IssueSink
from mister.catalog.infrastructure.content_schema.reader import read_tree
from mister.catalog.infrastructure.content_schema.release import check_release
from mister.catalog.infrastructure.content_schema.season_checks import (
    SeasonChecker,
    check_playable_rationales,
)
from mister.catalog.infrastructure.content_schema.tree import ContentTree


def load_content_tree(root: Path, *, release: bool) -> ContentTree:
    """Load and validate the content tree under `root`.

    Checks the schema of every file, the referential integrity between files and, with
    `release=True`, that nothing is `verify: pending` or a `draft` text.

    Raises:
        ContentValidationError: with *all* the issues found (file path, field and message),
            not just the first one.
    """
    sink = IssueSink()
    result = read_tree(root, sink)
    tree = result.tree
    check_club_references(tree, sink)
    check_players_across_squads(tree, sink)
    for slug in tree.seasons:
        SeasonChecker(tree, result.failed_club_seasons, slug, sink).run()
    check_playable_rationales(tree, sink)
    if release:
        check_release(tree, sink)
    if sink.issues:
        raise ContentValidationError(sink.issues)
    return tree
