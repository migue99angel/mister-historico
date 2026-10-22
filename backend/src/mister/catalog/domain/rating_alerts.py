"""Anti-inflation alerts of a squad's ratings (rubric section 6.1).

They are warnings to review the *data* (a statistic copied wrongly, a wrong club level), never
errors and never a reason to edit a rating by hand. Two alerts of the rubric need information
this module does not have and are not implemented here: the average of the starting eleven
(needs the lineup rules of the simulation) and the world quotas per band (need every player).
"""

from collections.abc import Sequence
from dataclasses import dataclass

STAR_RATING = 88
MAX_STARS = 2
GOOD_RATING = 80
MAX_GOOD = 6
ELITE_RATING = 90
ELITE_MAX_YOUNG_AGE = 21
ELITE_MIN_OLD_AGE = 35


@dataclass(frozen=True, slots=True)
class RatedPlayer:
    """A player's final rating with his age, which may be unknown."""

    player_id: str
    rating: int
    age: int | None


def rating_alerts(players: Sequence[RatedPlayer]) -> tuple[str, ...]:
    """Alerts for one squad, in a stable order."""
    alerts: list[str] = []
    stars = sum(1 for p in players if p.rating >= STAR_RATING)
    if stars > MAX_STARS:
        alerts.append(f"more than {MAX_STARS} players of {STAR_RATING}+ ({stars})")
    good = sum(1 for p in players if p.rating >= GOOD_RATING)
    if good > MAX_GOOD:
        alerts.append(f"more than {MAX_GOOD} players of {GOOD_RATING}+ ({good})")
    for player in players:
        if player.rating < ELITE_RATING or player.age is None:
            continue
        if player.age <= ELITE_MAX_YOUNG_AGE or player.age >= ELITE_MIN_OLD_AGE:
            alerts.append(
                f"{player.player_id}: rating {player.rating} at age {player.age}; "
                "check the statistics were copied right"
            )
    return tuple(alerts)
