from datetime import datetime, timedelta, timezone

import pytest

from app.models.activity import Activity
from app.services.xp_engine import skill_formulas


def _activity(**overrides) -> Activity:
    defaults = dict(
        activity_type="running",
        start_time=datetime(2026, 7, 10, tzinfo=timezone.utc),
        duration_seconds=1800.0,  # 30 min
        distance_meters=5000.0,  # 5 km -> pace 2.778 m/s
        avg_hr=150,
    )
    defaults.update(overrides)
    return Activity(**defaults)


# --- speed ---


def test_speed_gives_baseline_with_no_history() -> None:
    assert skill_formulas.speed_skill_xp(_activity(), []) == skill_formulas.SKILL_BASE_XP


def test_speed_rewards_matching_personal_best() -> None:
    history = [_activity(duration_seconds=1800.0, distance_meters=5000.0)]  # same pace
    xp = skill_formulas.speed_skill_xp(_activity(), history)
    assert xp == pytest.approx(skill_formulas.SKILL_BASE_XP)  # ratio 1.0


def test_speed_caps_bonus_for_a_new_pr() -> None:
    history = [_activity(duration_seconds=3600.0, distance_meters=5000.0)]  # half the pace
    xp = skill_formulas.speed_skill_xp(_activity(), history)  # current pace is 2x history's best
    assert xp == pytest.approx(skill_formulas.SKILL_BASE_XP * skill_formulas.SPEED_RATIO_CAP)


def test_speed_floors_a_much_slower_effort() -> None:
    slow = _activity(duration_seconds=7200.0, distance_meters=5000.0)  # much slower than history
    history = [_activity(duration_seconds=1200.0, distance_meters=5000.0)]  # fast history
    xp = skill_formulas.speed_skill_xp(slow, history)
    assert xp == pytest.approx(skill_formulas.SKILL_BASE_XP * skill_formulas.RATIO_FLOOR)


def test_speed_zero_for_degenerate_activity() -> None:
    assert skill_formulas.speed_skill_xp(_activity(duration_seconds=0), []) == 0.0


# --- endurance ---


def test_endurance_gives_baseline_with_no_history() -> None:
    assert skill_formulas.endurance_skill_xp(_activity(), []) == skill_formulas.SKILL_BASE_XP


def test_endurance_rewards_going_further_than_average() -> None:
    history = [_activity(distance_meters=2500.0), _activity(distance_meters=2500.0)]
    long_run = _activity(distance_meters=5000.0)  # 2x the rolling average
    xp = skill_formulas.endurance_skill_xp(long_run, history)
    assert xp == pytest.approx(skill_formulas.SKILL_BASE_XP * skill_formulas.ENDURANCE_RATIO_CAP)


def test_endurance_floors_a_much_shorter_activity() -> None:
    history = [_activity(distance_meters=10000.0)]
    short = _activity(distance_meters=500.0)
    xp = skill_formulas.endurance_skill_xp(short, history)
    assert xp == pytest.approx(skill_formulas.SKILL_BASE_XP * skill_formulas.RATIO_FLOOR)


# --- health ---


def test_health_gives_baseline_with_no_similar_pace_history() -> None:
    assert skill_formulas.health_skill_xp(_activity(), []) == skill_formulas.SKILL_BASE_XP


def test_health_rewards_lower_hr_at_similar_pace() -> None:
    # same pace as current (2.778 m/s), but historically averaged 170 bpm
    history = [_activity(avg_hr=170), _activity(avg_hr=170)]
    efficient = _activity(avg_hr=136)  # 170/136 ~= 1.25
    xp = skill_formulas.health_skill_xp(efficient, history)
    assert xp == pytest.approx(skill_formulas.SKILL_BASE_XP * (170 / 136))


def test_health_ignores_dissimilar_pace_history() -> None:
    # history pace is way slower (3600s for 5000m vs current 1800s) -> outside the 15% band
    history = [_activity(duration_seconds=3600.0, distance_meters=5000.0, avg_hr=110)]
    xp = skill_formulas.health_skill_xp(_activity(avg_hr=150), history)
    assert xp == skill_formulas.SKILL_BASE_XP  # falls back to baseline, ignoring the dissimilar entry


def test_health_zero_without_hr_data() -> None:
    assert skill_formulas.health_skill_xp(_activity(avg_hr=None), []) == 0.0


# --- consistency ---


def test_consistency_gives_baseline_for_first_ever_activity() -> None:
    assert skill_formulas.consistency_skill_xp(_activity(), []) == skill_formulas.SKILL_BASE_XP


def test_consistency_rewards_showing_up_immediately() -> None:
    yesterday = _activity(start_time=datetime(2026, 7, 9, tzinfo=timezone.utc))
    today = _activity(start_time=datetime(2026, 7, 10, tzinfo=timezone.utc))
    xp = skill_formulas.consistency_skill_xp(today, [yesterday])
    # gap_days ~= 1 -> ratio = 2 - 1/3 = 1.667, capped at CONSISTENCY_RATIO_CAP
    assert xp == pytest.approx(skill_formulas.SKILL_BASE_XP * skill_formulas.CONSISTENCY_RATIO_CAP)


def test_consistency_floors_a_long_gap() -> None:
    long_ago = _activity(start_time=datetime(2026, 6, 1, tzinfo=timezone.utc))
    today = _activity(start_time=datetime(2026, 7, 10, tzinfo=timezone.utc))
    xp = skill_formulas.consistency_skill_xp(today, [long_ago])
    assert xp == pytest.approx(skill_formulas.SKILL_BASE_XP * skill_formulas.RATIO_FLOOR)


def test_consistency_handles_out_of_order_history_defensively() -> None:
    future_looking = _activity(start_time=datetime(2026, 7, 20, tzinfo=timezone.utc))
    today = _activity(start_time=datetime(2026, 7, 10, tzinfo=timezone.utc))
    xp = skill_formulas.consistency_skill_xp(today, [future_looking])
    assert xp == pytest.approx(skill_formulas.SKILL_BASE_XP * skill_formulas.CONSISTENCY_RATIO_CAP)


# --- explorer ---


def test_explorer_awards_xp_only_on_new_course_discovery() -> None:
    activity = _activity()
    activity._is_new_course_discovery = True
    assert skill_formulas.explorer_skill_xp(activity, []) == skill_formulas.EXPLORER_DISCOVERY_XP


def test_explorer_awards_nothing_for_a_repeat_run() -> None:
    activity = _activity()
    activity._is_new_course_discovery = False
    assert skill_formulas.explorer_skill_xp(activity, []) == 0.0


def test_explorer_awards_nothing_when_flag_is_absent() -> None:
    assert skill_formulas.explorer_skill_xp(_activity(), []) == 0.0
