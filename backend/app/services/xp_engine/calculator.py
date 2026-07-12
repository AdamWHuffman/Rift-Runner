"""Orchestrates one activity -> base XP, multipliers, an xp_transactions
row, and main-level leveling progress.

xp_type="main" / target_key="main" is the only combination used here. Skills
(xp_engine/skills.py) and course mastery (course_engine/course_service.py)
call the same leveling primitive with their own target_key and their own
independent EMA state, producing their own xp_transactions rows from the
same activity.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import Activity
from app.models.goal import Goal
from app.models.user import User
from app.models.xp_transaction import XPTransaction
from app.services.xp_engine import formulas, leveling

FORMULA_VERSION = 1


def process_activity(
    db: AsyncSession,
    user: User,
    activity: Activity,
    course_difficulty_rating: int | None = None,
    active_goal: Goal | None = None,
) -> list[leveling.LevelUpEvent]:
    """Compute and apply this activity's main XP. Does not commit -- the
    caller controls the transaction boundary.

    course_difficulty_rating should be this user's frozen difficulty rating
    for the activity's matched course (course_service resolves this before
    calling here), or None if the activity has no matched course yet.
    active_goal is the user's currently active Goal row, or None if they
    haven't set one -- goal_alignment stays neutral either way.
    """
    base = formulas.base_xp(activity)
    multipliers = {
        "elevation": formulas.elevation_multiplier(activity),
        "pr_bonus": formulas.pr_bonus_multiplier(activity),
        "course_difficulty": formulas.course_difficulty_multiplier(course_difficulty_rating, user.main_level),
        "goal_alignment": formulas.goal_alignment_multiplier(
            activity.hr_seconds_in_zone,
            active_goal.zone_weight_targets if active_goal else None,
            active_goal.multiplier_min if active_goal else 0.7,
            active_goal.multiplier_max if active_goal else 1.3,
        ),
    }
    final_xp = base
    for value in multipliers.values():
        final_xp *= value
    final_xp = round(final_xp)

    state = leveling.LevelingState(
        level=user.main_level,
        xp_into_level=user.xp_into_level,
        xp_to_next_level_snapshot=user.xp_to_next_level_snapshot,
        activities_this_level=user.activities_this_level,
        avg_xp_per_activity_ema=user.avg_xp_per_activity_ema,
    )
    result = leveling.apply_progress(state, final_xp)
    level_before = user.main_level

    user.main_level = result.state.level
    user.xp_into_level = result.state.xp_into_level
    user.xp_to_next_level_snapshot = result.state.xp_to_next_level_snapshot
    user.activities_this_level = result.state.activities_this_level
    user.avg_xp_per_activity_ema = result.state.avg_xp_per_activity_ema
    user.main_xp_total += final_xp

    db.add(
        XPTransaction(
            user_id=user.id,
            activity_id=activity.id,
            xp_type="main",
            target_key="main",
            base_xp=base,
            multipliers=multipliers,
            final_xp=final_xp,
            formula_version=FORMULA_VERSION,
            level_before=level_before,
            level_after=result.state.level,
            goal_id_at_time=active_goal.id if active_goal else None,
        )
    )

    return result.level_ups
