import pytest

from app.models.activity import Activity
from app.services.xp_engine import formulas


def _activity(**overrides) -> Activity:
    defaults = dict(
        activity_type="running",
        duration_seconds=1920.0,
        distance_meters=5200.0,
        elevation_gain_meters=60.0,
        calories=400.0,
        hr_seconds_in_zone=None,
        is_personal_record=False,
    )
    defaults.update(overrides)
    return Activity(**defaults)


def test_base_xp_trimp_matches_worked_example_from_plan() -> None:
    # 3 / 15 / 13 / 1 / 0 minutes in zones 1-5 -> trimp 76 -> base_xp 760
    activity = _activity(hr_seconds_in_zone={"1": 180, "2": 900, "3": 780, "4": 60, "5": 0})

    assert formulas.base_xp(activity) == pytest.approx(760.0)


def test_base_xp_falls_back_to_calories_and_duration_without_hr_data() -> None:
    activity = _activity(hr_seconds_in_zone=None, calories=400.0, duration_seconds=1800.0)

    # 400 * 0.5 + 30 * 1.5 = 200 + 45 = 245
    assert formulas.base_xp(activity) == pytest.approx(245.0)


def test_base_xp_fallback_handles_missing_calories() -> None:
    activity = _activity(hr_seconds_in_zone=None, calories=None, duration_seconds=1200.0)

    assert formulas.base_xp(activity) == pytest.approx(30.0)  # 20 min * 1.5


def test_elevation_multiplier_matches_worked_example_from_plan() -> None:
    # 60m gain over 5.2km -> 11.5 m/km (plan's rounded figure) -> ~+11.5% -> ~1.115
    activity = _activity(elevation_gain_meters=60.0, distance_meters=5200.0)

    assert formulas.elevation_multiplier(activity) == pytest.approx(1.115, abs=1e-3)


def test_elevation_multiplier_caps_at_fifty_percent() -> None:
    activity = _activity(elevation_gain_meters=10000.0, distance_meters=1000.0)

    assert formulas.elevation_multiplier(activity) == pytest.approx(1.5)


def test_elevation_multiplier_no_bonus_when_flat() -> None:
    activity = _activity(elevation_gain_meters=0.0, distance_meters=5000.0)

    assert formulas.elevation_multiplier(activity) == pytest.approx(1.0)


def test_elevation_multiplier_handles_zero_distance() -> None:
    activity = _activity(elevation_gain_meters=50.0, distance_meters=0.0)

    assert formulas.elevation_multiplier(activity) == 1.0


def test_pr_bonus_multiplier_applies_flat_bonus_when_flagged() -> None:
    assert formulas.pr_bonus_multiplier(_activity(is_personal_record=True)) == pytest.approx(1.5)


def test_pr_bonus_multiplier_neutral_when_not_a_pr() -> None:
    assert formulas.pr_bonus_multiplier(_activity(is_personal_record=False)) == pytest.approx(1.0)
    assert formulas.pr_bonus_multiplier(_activity(is_personal_record=None)) == pytest.approx(1.0)
