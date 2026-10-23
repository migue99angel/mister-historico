"""Print the anchor calibration table (T1.7b) from `content/anchors/`.

Run from `backend/`:  uv run python tests/content/anchors/report.py [--write]

It reads only `content/anchors/` and computes every rating with `compute_rating`, the same
function behind `mister content ratings compute`. With `--write` it also stores the final
ratings (formula, or override when there is one) in the squad files, as the CLI does.
"""

import sys
from pathlib import Path

import yaml

from mister.catalog.application.ratings_tool import RatingsTool
from mister.catalog.infrastructure.content_schema.rating_sheets import YamlRatingSheetStore

ROOT = Path(__file__).resolve().parents[3].parent / "content" / "anchors"


def band_gap(rating: int, band: str) -> int:
    """Points outside the band (0 when inside, negative below)."""
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
    lines = {}
    for club_season in sorted({anchor["club_season"] for anchor in bands}):
        report = tool.compute(club_season) if write else tool.check(club_season)
        for line in report.lines:
            lines[(club_season, line.player_id)] = line
    emit(
        "| Banda | Jugador | Temporada | Clave | Base | Desv. base | Override | Final |"
        " Desv. final |"
    )
    emit("|---|---|---|---|---|---|---|---|---|")
    stats: dict[str, list[tuple[int, int]]] = {"non_key": [], "key": []}
    rows = sorted(bands, key=lambda a: (-int(a["band"].split("-")[0]), a["club_season"]))
    for anchor in rows:
        line = lines[(anchor["club_season"], anchor["player_id"])]
        base, final = line.result.rating, line.expected
        assert base is not None
        assert final is not None
        base_gap = band_gap(base, anchor["band"])
        final_gap = band_gap(final, anchor["band"])
        stats["key" if anchor["key"] else "non_key"].append((base_gap, final_gap))
        override = "" if line.override_value is None else str(line.override_value)
        emit(
            f"| {anchor['band']} | {anchor['player_id']} | {anchor['club_season'][8:]} "
            f"| {'si' if anchor['key'] else 'no'} | {base} | {base_gap:+d} | {override} "
            f"| {final} | {final_gap:+d} |"
        )
    non_key = stats["non_key"]
    key = stats["key"]
    emit("")
    emit(
        f"no clave (formula sola): {sum(g != 0 for g, _ in non_key)} de {len(non_key)} fuera; "
        f"mayor desviacion {max((abs(g) for g, _ in non_key), default=0)}"
    )
    emit(
        f"clave (base): {sum(g != 0 for g, _ in key)} de {len(key)} fuera; "
        f"mayor desviacion {max((abs(g) for g, _ in key), default=0)}"
    )
    emit(
        f"clave (tras la revision): {sum(f != 0 for _, f in key)} de {len(key)} fuera; "
        f"mayor desviacion {max((abs(f) for _, f in key), default=0)}"
    )


if __name__ == "__main__":
    main()
