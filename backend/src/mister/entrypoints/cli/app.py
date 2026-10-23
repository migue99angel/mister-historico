"""The `mister` command: `mister content ratings compute <club-season>` and friends."""

from pathlib import Path
from typing import Annotated

import typer

from mister.bootstrap import build_ratings_tool
from mister.catalog.application.ratings_tool import (
    PlayerRatingLine,
    RatingsReport,
)
from mister.shared_kernel.errors import DomainError

EXIT_DISCREPANCY = 1
EXIT_ERROR = 2

app = typer.Typer(help="Míster Histórico command line tools.", no_args_is_help=True)
content_app = typer.Typer(help="Historical content tools.", no_args_is_help=True)
ratings_app = typer.Typer(help="Player ratings (ADR-006).", no_args_is_help=True)
app.add_typer(content_app, name="content")
content_app.add_typer(ratings_app, name="ratings")


@ratings_app.command("compute")
def compute(
    club_season: Annotated[
        str, typer.Argument(help="Slug of the club-season, e.g. test-fc-2000-01.")
    ],
    root: Annotated[
        Path | None,
        typer.Option(help="Content directory (default: ./content, else the repository's)."),
    ] = None,
    check: Annotated[
        bool, typer.Option("--check", help="Write nothing; exit 1 if a rating is out of date.")
    ] = False,
    explain: Annotated[
        str | None,
        typer.Option("--explain", metavar="PLAYER_ID", help="Print the breakdown of one player."),
    ] = None,
) -> None:
    """Compute the ratings of a club-season from its statistics and write them in its squad.

    The formula is `docs/content/rating-rubric.md`, section 4. With `--check` nothing is
    written and the exit code is 1 when a stored rating differs from the formula (or from its
    override), which makes it usable in CI. Exit code 2 means the club-season could not be read.
    """
    tool = build_ratings_tool(_content_root(root))
    try:
        if explain is not None:
            typer.echo(_explanation(tool.explain(club_season, explain)))
            return
        report = tool.check(club_season) if check else tool.compute(club_season)
    except DomainError as error:
        typer.echo(f"error: {error}", err=True)
        raise typer.Exit(EXIT_ERROR) from error
    _print_report(report, check=check)
    if report.problems or (check and report.discrepancies):
        raise typer.Exit(EXIT_DISCREPANCY)


def _content_root(root: Path | None) -> Path:
    """The given root; else `./content`; else the `content/` of the repository this package is in.

    The last fallback makes the command work from `backend/`, where `uv run` is used.
    """
    if root is not None:
        return root
    local = Path("content")
    repository = Path(__file__).resolve().parents[5] / "content"
    if not local.is_dir() and repository.is_dir():
        return repository
    return local


def _print_report(report: RatingsReport, *, check: bool) -> None:
    for line in report.lines:
        if line.problem is not None:
            typer.echo(f"{line.player_id}: rating_override {line.problem}")
        elif line.stale:
            action = "expected" if check else "updated to"
            typer.echo(
                f"{line.player_id}: stored {_value(line.stored)}, {action} {_value(line.expected)}"
                f"{_why(line)}"
            )
    for line in report.lines:
        if line.notes:
            typer.echo(f"note: {line.player_id}: {'; '.join(line.notes)}")
    for alert in report.alerts:
        typer.echo(f"warning: {alert}")
    stale = sum(1 for line in report.lines if line.stale)
    if not stale and not report.problems:
        typer.echo(f"{report.club_season}: {len(report.lines)} ratings up to date")
    elif report.written:
        typer.echo(f"{report.club_season}: {stale} of {len(report.lines)} ratings written")
    else:
        typer.echo(f"{report.club_season}: {stale} of {len(report.lines)} ratings out of date")


def _value(rating: int | None) -> str:
    return "null" if rating is None else str(rating)


def _why(line: PlayerRatingLine) -> str:
    if line.overridden:
        return " (rating_override)"
    if line.result.rating is None:
        return f" (missing: {', '.join(line.result.missing)})"
    return ""


def _explanation(line: PlayerRatingLine) -> str:
    result = line.result
    head = f"{line.player_id} ({line.display_name})"
    if result.components is None or result.raw is None:
        return f"{head}\n  rating: null (missing: {', '.join(result.missing)})"
    parts = result.components
    rows = [
        head,
        f"  basis        {result.basis}",
        f"  importance   {float(parts.importance):.4f}  (x22)",
        f"  production   {float(parts.production):.4f}  (x14)",
        f"  selection    {float(parts.selection):.4f}  (x6)",
        f"  awards       {float(parts.awards):.4f}  (x7)",
        f"  level        {parts.level:+d}",
        f"  raw          {float(result.raw):.6f}  = 46 + 22 I + 14 P + 6 N + 7 V + T",
        f"  formula      {result.rating}",
    ]
    if line.overridden:
        rows.append(f"  override     {line.override_value}")
    rows.append(f"  stored       {_value(line.stored)}")
    if result.notes:
        rows.append(f"  notes        {'; '.join(result.notes)}")
    return "\n".join(rows)
