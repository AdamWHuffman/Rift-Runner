"""XP formula: a TRIMP-weighted effort base, times multiplicative bonus factors."""

from app.models.activity import Activity

ZONE_MINUTES_TO_XP = 10.0  # base_xp = trimp * this
CALORIE_FALLBACK_WEIGHT = 0.5
DURATION_FALLBACK_WEIGHT_PER_MINUTE = 1.5

ELEVATION_MAX_BONUS = 0.5
ELEVATION_SCALE = 0.01  # +1% per (meter of gain per km), up to the cap above

PR_BONUS = 0.5  # flat +50% when Garmin flags this activity as a personal record

COURSE_DIFFICULTY_MULTIPLIER_SCALE = 0.05
COURSE_DIFFICULTY_MULTIPLIER_MIN = -0.2
COURSE_DIFFICULTY_MULTIPLIER_MAX = 0.3


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


def course_difficulty_multiplier(difficulty_rating: int | None, user_main_level: int) -> float:
    """Tackling a course rated above your level pays more; an easy course
    never fully zeroes out. Neutral (1.0) when the activity has no matched
    course yet (e.g. no GPS data)."""
    if difficulty_rating is None:
        return 1.0
    delta = (difficulty_rating - user_main_level) * COURSE_DIFFICULTY_MULTIPLIER_SCALE
    bonus = max(COURSE_DIFFICULTY_MULTIPLIER_MIN, min(COURSE_DIFFICULTY_MULTIPLIER_MAX, delta))
    return 1.0 + bonus


def goal_alignment_multiplier(
    hr_seconds_in_zone: dict | None,
    zone_weight_targets: list[float] | None,
    multiplier_min: float = 0.7,
    multiplier_max: float = 1.3,
) -> float:
    """Compares this activity's actual HR-zone-time distribution to the
    user's active goal's target distribution -- a closer match pays more.
    Neutral (1.0) with no HR data or no active goal, so this never punishes
    users who haven't set a goal yet or activities without HR data.

    Similarity is 1 minus the normalized L1 distance between the two
    5-element distributions (each summing to ~1.0), linearly mapped into the
    goal's [multiplier_min, multiplier_max] range.
    """
    if not hr_seconds_in_zone or not zone_weight_targets:
        return 1.0

    total_seconds = sum(hr_seconds_in_zone.values())
    if total_seconds <= 0:
        return 1.0

    actual_fractions = [hr_seconds_in_zone.get(str(zone), 0.0) / total_seconds for zone in range(1, 6)]
    l1_distance = sum(abs(a - t) for a, t in zip(actual_fractions, zone_weight_targets))
    similarity = max(0.0, 1.0 - l1_distance / 2.0)

    return multiplier_min + similarity * (multiplier_max - multiplier_min)
