"""Print the anchor calibration table (T1.7b) from `content/anchors/`.

Run from `backend/`:  uv run python tests/content/anchors/report.py [--write]

It reads only `content/anchors/` and computes every rating with `compute_rating`, the same
function behind `mister content ratings compute`. With `--write` it also stores the formula's
ratings in the squad files, as the CLI does.
"""

import sys
from pathlib import Path

import yaml

from mister.catalog.application.ratings_tool import RatingsTool
from mister.catalog.infrastructure.content_schema.rating_sheets import YamlRatingSheetStore

ROOT = Path(__file__).resolve().parents[3].parent / "content" / "anchors"


def band_gap(rating: int, band: str) -> int:
    """Points outside the band (0 when inside)."""
    low, high = (int(part) for part in band.split("-"))
    if rating < low:
        return rating - low
    return max(0, rating - high)


def emit(text: str) -> None:
    sys.stdout.write(text + "\n")


def main() -> None:
    write = "--write" in sys.argv
    bands = yaml.safe_load((ROOT / "bands.yaml").read_text(encoding="utf-8"))["anchors"]
    tool = RatingsTool(YamlRatingSheetStore(ROOT))
    seasons = sorted({anchor["club_season"] for anchor in bands})
    lines = {}
    for club_season in seasons:
        report = tool.compute(club_season) if write else tool.check(club_season)
        for line in report.lines:
            lines[(club_season, line.player_id)] = line
    emit("| Banda | Jugador | Temporada | Media | Desv. | I | P | N | V | T | Base | Notas |")
    emit("|---|---|---|---|---|---|---|---|---|---|---|---|")
    outside = 0
    worst = 0
    for anchor in bands:
        line = lines[(anchor["club_season"], anchor["player_id"])]
        rating = line.result.rating
        comp = line.result.components
        assert rating is not None
        assert comp is not None
        gap = band_gap(rating, anchor["band"])
        outside += gap != 0
        worst = max(worst, abs(gap))
        notes = "; ".join(line.notes)
        emit(
            f"| {anchor['band']} | {anchor['player_id']} | {anchor['club_season'][8:]} | {rating} "
            f"| {gap:+d} | {float(comp.importance):.2f} | {float(comp.production):.2f} "
            f"| {float(comp.selection):.2f} | {float(comp.awards):.2f} | {comp.level:+d} "
            f"| {line.result.basis} | {notes} |"
        )
    emit(f"\nfuera de banda: {outside} de {len(bands)}; mayor desviacion: {worst}")


if __name__ == "__main__":
    main()
