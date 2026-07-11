"""XP formula: a TRIMP-weighted effort base, times multiplicative bonus factors.

course_difficulty and goal_alignment are stubbed at a neutral 1.0 in
calculator.py -- Phase 5 (courses) and Phase 6 (goals) wire in real logic
without needing to touch this module's shape or the formula's overall
structure.
"""

from app.models.activity import Activity

ZONE_MINUTES_TO_XP = 10.0  # base_xp = trimp * this
CALORIE_FALLBACK_WEIGHT = 0.5
DURATION_FALLBACK_WEIGHT_PER_MINUTE = 1.5

ELEVATION_MAX_BONUS = 0.5
ELEVATION_SCALE = 0.01  # +1% per (meter of gain per km), up to the cap above

PR_BONUS = 0.5  # flat +50% when Garmin flags this activity as a personal record


def base_xp(activity: Activity) -> float:
    """TRIMP-weighted effort (heart-rate zone time, weighted by zone) when HR
    data is available; a calories+duration fallback otherwise."""
    if activity.hr_seconds_in_zone:
        trimp = sum((seconds / 60.0) * int(zone) for zone, seconds in activity.hr_seconds_in_zone.items())
        return trimp * ZONE_MINUTES_TO_XP

    duration_minutes = activity.duration_seconds / 60.0
    calories = activity.calories or 0.0
    return calories * CALORIE_FALLBACK_WEIGHT + duration_minutes * DURATION_FALLBACK_WEIGHT_PER_MINUTE


def elevation_multiplier(activity: Activity) -> float:
    """Up to +50% for steep routes; a flat or indoor activity gets no bonus."""
    if activity.distance_meters <= 0:
        return 1.0
    gain_per_km = activity.elevation_gain_meters / (activity.distance_meters / 1000.0)
    bonus = min(ELEVATION_MAX_BONUS, max(0.0, gain_per_km * ELEVATION_SCALE))
    return 1.0 + bonus


def pr_bonus_multiplier(activity: Activity) -> float:
    """Garmin's own personal-record flag, used as a simple signal for now.

    Phase 5 replaces this with our own multi-factor PR detection (course-best
    time, pace, distance) once course tracking exists to compare against.
    """
    return 1.0 + PR_BONUS if activity.is_personal_record else 1.0
