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


def test_course_difficulty_multiplier_neutral_when_no_course() -> None:
    assert formulas.course_difficulty_multiplier(None, user_main_level=5) == pytest.approx(1.0)


def test_course_difficulty_multiplier_rewards_harder_than_your_level() -> None:
    # difficulty 20, user level 5 -> delta 15 * 0.05 = 0.75, capped at +0.3
    assert formulas.course_difficulty_multiplier(20, user_main_level=5) == pytest.approx(1.3)


def test_course_difficulty_multiplier_penalizes_easier_than_your_level() -> None:
    # difficulty 5, user level 20 -> delta -15 * 0.05 = -0.75, floored at -0.2
    assert formulas.course_difficulty_multiplier(5, user_main_level=20) == pytest.approx(0.8)


def test_course_difficulty_multiplier_never_fully_zeroes_out() -> None:
    multiplier = formulas.course_difficulty_multiplier(1, user_main_level=99)
    assert multiplier >= 1.0 + formulas.COURSE_DIFFICULTY_MULTIPLIER_MIN


# --- heat_multiplier ---


def test_heat_multiplier_neutral_when_no_weather_data() -> None:
    assert formulas.heat_multiplier(None) == pytest.approx(1.0)


def test_heat_multiplier_neutral_below_caution_threshold() -> None:
    # A comfortable 20C day shouldn't get a bonus, only genuinely hot ones.
    assert formulas.heat_multiplier(20.0) == pytest.approx(1.0)
    assert formulas.heat_multiplier(formulas.HEAT_INDEX_THRESHOLD_C) == pytest.approx(1.0)


def test_heat_multiplier_scales_linearly_between_caution_and_danger() -> None:
    midpoint = (formulas.HEAT_INDEX_THRESHOLD_C + formulas.HEAT_INDEX_DANGER_C) / 2
    multiplier = formulas.heat_multiplier(midpoint)
    assert multiplier == pytest.approx(1.0 + formulas.HEAT_MAX_BONUS / 2)


def test_heat_multiplier_caps_at_max_bonus_for_dangerous_heat() -> None:
    assert formulas.heat_multiplier(formulas.HEAT_INDEX_DANGER_C) == pytest.approx(1.0 + formulas.HEAT_MAX_BONUS)
    # Even more extreme heat doesn't pay more than the cap.
    assert formulas.heat_multiplier(50.0) == pytest.approx(1.0 + formulas.HEAT_MAX_BONUS)


# --- goal_alignment_multiplier ---

BASE_BUILDING_TARGETS = [0.20, 0.35, 0.30, 0.10, 0.05]


def test_goal_alignment_neutral_without_hr_data() -> None:
    assert formulas.goal_alignment_multiplier(None, BASE_BUILDING_TARGETS) == pytest.approx(1.0)
    assert formulas.goal_alignment_multiplier({}, BASE_BUILDING_TARGETS) == pytest.approx(1.0)


def test_goal_alignment_neutral_without_active_goal() -> None:
    assert formulas.goal_alignment_multiplier({"1": 600, "2": 600}, None) == pytest.approx(1.0)


def test_goal_alignment_maximal_when_distribution_matches_exactly() -> None:
    # Exactly matches base_building's [0.20, 0.35, 0.30, 0.10, 0.05] target.
    zones = {"1": 200.0, "2": 350.0, "3": 300.0, "4": 100.0, "5": 50.0}  # sums to 1000
    multiplier = formulas.goal_alignment_multiplier(zones, BASE_BUILDING_TARGETS, 0.7, 1.3)
    assert multiplier == pytest.approx(1.3, abs=1e-6)


def test_goal_alignment_minimal_when_distribution_is_opposite() -> None:
    # All time in zone 5, but base_building wants mostly zone 1-3.
    zones = {"5": 1000.0}
    multiplier = formulas.goal_alignment_multiplier(zones, BASE_BUILDING_TARGETS, 0.7, 1.3)
    assert multiplier == pytest.approx(0.7, abs=0.05)


def test_goal_alignment_rewards_easy_effort_for_base_building_but_not_racing() -> None:
    # A very easy, all-zone-2 activity: great for base_building, mediocre for racing.
    easy_zones = {"2": 1000.0}
    racing_targets = [0.05, 0.10, 0.20, 0.35, 0.30]

    base_building_score = formulas.goal_alignment_multiplier(easy_zones, BASE_BUILDING_TARGETS)
    racing_score = formulas.goal_alignment_multiplier(easy_zones, racing_targets)

    assert base_building_score > racing_score


def test_goal_alignment_zone_three_scores_well_for_base_building() -> None:
    # User's own correction: zone 3 is still aerobic and should be rewarded
    # nearly as well as zone 2 for base_building, unlike zones 4-5.
    zone_two = formulas.goal_alignment_multiplier({"2": 1000.0}, BASE_BUILDING_TARGETS)
    zone_three = formulas.goal_alignment_multiplier({"3": 1000.0}, BASE_BUILDING_TARGETS)
    zone_five = formulas.goal_alignment_multiplier({"5": 1000.0}, BASE_BUILDING_TARGETS)

    assert zone_three == pytest.approx(zone_two, abs=0.15)
    assert zone_three > zone_five
