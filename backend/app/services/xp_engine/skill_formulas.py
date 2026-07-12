"""Pure per-skill XP formulas.

Each takes the current activity plus the user's own relevant history (already
fetched by the caller) and returns raw skill XP. No DB access here -- keeps
these easy to unit test and keeps the "what counts as history" decision
(same activity type vs. all types) in the orchestration layer, not here.

A ratio-based design throughout: compare this activity to the user's own
recent baseline, with both a floor (so an off day still earns something) and
a cap (so one outlier doesn't trivialize the skill). A brand-new track with
no history yet gets a flat baseline award rather than zero, so skills start
building from the very first activity.
"""

from app.models.activity import Activity

SKILL_BASE_XP = 150.0
EXPLORER_DISCOVERY_XP = 200.0

RATIO_FLOOR = 0.3
SPEED_RATIO_CAP = 1.5
ENDURANCE_RATIO_CAP = 2.0
HEALTH_RATIO_CAP = 1.5
CONSISTENCY_RATIO_CAP = 1.5
HEALTH_SIMILAR_PACE_BAND = 0.15  # +/- 15% pace to count as a comparable effort


def _pace_mps(activity: Activity) -> float | None:
    if activity.duration_seconds <= 0 or activity.distance_meters <= 0:
        return None
    return activity.distance_meters / activity.duration_seconds


def speed_skill_xp(activity: Activity, history: list[Activity]) -> float:
    """Rewards pace approaching or exceeding this user's own best -- a
    slow-but-improving effort still earns a meaningful floor."""
    current_pace = _pace_mps(activity)
    if current_pace is None:
        return 0.0

    past_paces = [p for p in (_pace_mps(a) for a in history) if p is not None]
    if not past_paces:
        return SKILL_BASE_XP

    best_pace = max(past_paces)
    if best_pace <= 0:
        return SKILL_BASE_XP

    ratio = max(RATIO_FLOOR, min(SPEED_RATIO_CAP, current_pace / best_pace))
    return SKILL_BASE_XP * ratio


def endurance_skill_xp(activity: Activity, history: list[Activity]) -> float:
    """Rewards distance relative to this user's own rolling average --
    progressive overload, not an absolute distance target."""
    if activity.distance_meters <= 0:
        return 0.0

    past_distances = [a.distance_meters for a in history if a.distance_meters > 0]
    if not past_distances:
        return SKILL_BASE_XP

    avg_distance = sum(past_distances) / len(past_distances)
    if avg_distance <= 0:
        return SKILL_BASE_XP

    ratio = max(RATIO_FLOOR, min(ENDURANCE_RATIO_CAP, activity.distance_meters / avg_distance))
    return SKILL_BASE_XP * ratio


def health_skill_xp(activity: Activity, history: list[Activity]) -> float:
    """Rewards a lower heart rate than this user's own typical HR for a
    similar pace -- better cardiovascular efficiency for the same effort."""
    current_pace = _pace_mps(activity)
    if current_pace is None or activity.avg_hr is None:
        return 0.0

    similar_effort_hrs = []
    for past in history:
        past_pace = _pace_mps(past)
        if past_pace is None or past.avg_hr is None:
            continue
        if abs(past_pace - current_pace) / current_pace <= HEALTH_SIMILAR_PACE_BAND:
            similar_effort_hrs.append(past.avg_hr)

    if not similar_effort_hrs:
        return SKILL_BASE_XP

    baseline_hr = sum(similar_effort_hrs) / len(similar_effort_hrs)
    if baseline_hr <= 0 or activity.avg_hr <= 0:
        return SKILL_BASE_XP

    ratio = max(RATIO_FLOOR, min(HEALTH_RATIO_CAP, baseline_hr / activity.avg_hr))
    return SKILL_BASE_XP * ratio


def consistency_skill_xp(activity: Activity, history: list[Activity]) -> float:
    """Rewards showing up again soon after the last activity (any type) --
    the direct habit-loop lever. A broken streak still earns the floor."""
    if not history:
        return SKILL_BASE_XP

    most_recent = max(history, key=lambda a: a.start_time)
    gap_days = max(0.0, (activity.start_time - most_recent.start_time).total_seconds() / 86400.0)

    ratio = max(RATIO_FLOOR, min(CONSISTENCY_RATIO_CAP, 2.0 - gap_days / 3.0))
    return SKILL_BASE_XP * ratio


def explorer_skill_xp(activity: Activity, history: list[Activity]) -> float:
    """Rewards discovering a brand-new course (and, by extension, possibly a
    brand-new region too) -- first-time-only, unlike the other skills there
    is no partial-credit floor here.

    Reads a transient flag set by course_service earlier in the same sync
    pass; deliberately never persisted on the Activity model since it's a
    one-time signal about this processing run, not a lasting fact about the
    activity itself.
    """
    return EXPLORER_DISCOVERY_XP if getattr(activity, "_is_new_course_discovery", False) else 0.0
