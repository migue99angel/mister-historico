"""Anti-inflation alerts of the rubric (section 6.1): warnings, never errors."""

from mister.catalog.domain.rating_alerts import RatedPlayer, rating_alerts


def squad(*ratings: int, age: int | None = 27) -> list[RatedPlayer]:
    return [RatedPlayer(f"p{i}", rating, age) for i, rating in enumerate(ratings)]


def test_a_normal_squad_raises_no_alert() -> None:
    assert rating_alerts(squad(70, 65, 88, 88, 80, 80, 80, 80)) == ()


def test_more_than_two_players_of_88_or_more_raises_an_alert() -> None:
    alerts = rating_alerts(squad(88, 90, 95))

    assert any("more than 2 players of 88+" in alert for alert in alerts)


def test_more_than_six_players_of_80_or_more_raises_an_alert() -> None:
    alerts = rating_alerts(squad(80, 81, 82, 83, 84, 85, 86))

    assert any("more than 6 players of 80+" in alert for alert in alerts)


def test_a_90_rating_in_a_very_young_player_raises_an_alert() -> None:
    alerts = rating_alerts([RatedPlayer("kid", 90, 21)])

    assert any("kid" in alert and "age 21" in alert for alert in alerts)


def test_a_90_rating_in_a_veteran_raises_an_alert() -> None:
    alerts = rating_alerts([RatedPlayer("old", 91, 35)])

    assert any("old" in alert and "age 35" in alert for alert in alerts)


def test_a_90_rating_in_a_prime_age_player_or_without_age_raises_no_age_alert() -> None:
    assert rating_alerts([RatedPlayer("prime", 90, 27), RatedPlayer("unknown", 90, None)]) == ()


def test_a_rating_below_90_in_a_young_player_raises_no_alert() -> None:
    assert rating_alerts([RatedPlayer("kid", 89, 19)]) == ()
