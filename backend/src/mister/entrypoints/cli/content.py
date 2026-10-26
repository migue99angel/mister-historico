"""CLI adapter for validating the historical content tree."""

from pathlib import Path
from typing import Annotated

import typer

from mister.bootstrap import build_load_catalog, build_validate_content
from mister.catalog.application.load_types import (
    CatalogContentInvalidError,
    CatalogLoadUnavailableError,
)
from mister.catalog.application.validation_types import (
    ContentValidationUnavailableError,
    ValidationIssue,
)

EXIT_INVALID_CONTENT = 1
EXIT_UNAVAILABLE_CONTENT = 2


def _print_issues(issues: tuple[ValidationIssue, ...]) -> None:
    for issue in issues:
        location = f"{issue.path}:{issue.field}" if issue.field else issue.path
        typer.echo(f"{location}: {issue.message}")


def resolve_content_root(root: Path | None) -> Path:
    """Prefer an explicit root, then the current directory, then the repository root."""
    if root is not None:
        return root
    local = Path("content")
    repository = Path(__file__).resolve().parents[5] / "content"
    if not local.is_dir() and repository.is_dir():
        return repository
    return local


def validate_content(
    root: Annotated[
        Path | None,
        typer.Option(
            help="Directorio del contenido (por defecto: ./content o el del repositorio)."
        ),
    ] = None,
    release: Annotated[
        bool,
        typer.Option("--release", help="Exige datos históricos completos y textos revisados."),
    ] = False,
) -> None:
    """Print every validation issue; use exit 1 for data and exit 2 for unavailable IO."""
    try:
        report = build_validate_content(resolve_content_root(root)).execute(release=release)
    except ContentValidationUnavailableError as error:
        typer.echo(f"Error de lectura: {error}", err=True)
        raise typer.Exit(EXIT_UNAVAILABLE_CONTENT) from error

    if report.issues:
        _print_issues(report.issues)
        raise typer.Exit(EXIT_INVALID_CONTENT)

    count = report.season_count
    if count == 0:
        typer.echo("Contenido válido: 0 temporadas jugables (catálogo vacío)")
    elif count == 1:
        typer.echo("Contenido válido: 1 temporada jugable")
    else:
        typer.echo(f"Contenido válido: {count} temporadas jugables")


def load_catalog(
    root: Annotated[
        Path | None,
        typer.Option(
            help="Directorio del contenido (por defecto: ./content o el del repositorio)."
        ),
    ] = None,
) -> None:
    """Publish release content to PostgreSQL with an idempotent content hash."""
    try:
        with build_load_catalog() as loader:
            report = loader.execute(resolve_content_root(root))
    except CatalogContentInvalidError as error:
        _print_issues(error.issues)
        if not error.issues:
            typer.echo(f"Contenido no publicable: {error}")
        raise typer.Exit(EXIT_INVALID_CONTENT) from error
    except CatalogLoadUnavailableError as error:
        typer.echo(f"Error de carga: {error}", err=True)
        raise typer.Exit(EXIT_UNAVAILABLE_CONTENT) from error

    if report.changed:
        unit = "temporada jugable" if report.season_count == 1 else "temporadas jugables"
        typer.echo(f"Contenido cargado: {report.season_count} {unit}; hash {report.content_hash}")
    else:
        typer.echo(f"Catálogo sin cambios; hash {report.content_hash}")
