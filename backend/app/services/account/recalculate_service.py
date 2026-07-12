"""Rebuilds a user's entire derived progression (XP ledger, main level,
skills, course mastery) from their current `activities` rows.

Necessary any time the activity set itself changes after the fact --
deleting an activity, or importing one from before activities that were
already processed. The leveling/EMA math is inherently sequential (each
activity's XP feeds the target for the next), so there's no way to
correctly patch in a single change; the only consistent approach is to
wipe every derived row and replay the remaining activities in
chronological order, exactly the "recalculate_xp.py" mechanism the
original plan called for to keep the whole algorithm safely tunable.
"""

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import Activity
from app.models.course_activity_link import CourseActivityLink
from app.models.course_user_progress import CourseUserProgress
from app.models.goal import Goal
from app.models.skill_progress import SkillProgress
from app.models.user import User
from app.models.user_goal_history import UserGoalHistory
from app.models.xp_transaction import XPTransaction
from app.services.course_engine import course_service
from app.services.xp_engine import calculator, leveling, skills


async def _goal_active_at(db: AsyncSession, user_id, when) -> Goal | None:
    """The goal that was actually active at a given historical moment, per
    UserGoalHistory -- so replaying old activities doesn't silently switch
    them to whatever goal happens to be active today."""
    history = await db.scalar(
        select(UserGoalHistory)
        .where(
            UserGoalHistory.user_id == user_id,
            UserGoalHistory.activated_at <= when,
        )
        .where(or_(UserGoalHistory.deactivated_at.is_(None), UserGoalHistory.deactivated_at > when))
        .order_by(UserGoalHistory.activated_at.desc())
        .limit(1)
    )
    if history is None:
        return None
    return await db.get(Goal, history.goal_id)


async def recalculate_all(db: AsyncSession, user: User) -> None:
    """Wipes derived state (not the activities themselves) and replays
    every remaining activity, oldest first. Does not commit -- the caller
    controls the transaction boundary."""
    await db.execute(delete(XPTransaction).where(XPTransaction.user_id == user.id))
    await db.execute(
        delete(CourseActivityLink).where(
            CourseActivityLink.activity_id.in_(select(Activity.id).where(Activity.user_id == user.id))
        )
    )
    await db.execute(delete(CourseUserProgress).where(CourseUserProgress.user_id == user.id))
    await db.execute(delete(SkillProgress).where(SkillProgress.user_id == user.id))

    seed = leveling.initial_state()
    user.main_level = seed.level
    user.main_xp_total = 0.0
    user.xp_into_level = seed.xp_into_level
    user.xp_to_next_level_snapshot = seed.xp_to_next_level_snapshot
    user.activities_this_level = seed.activities_this_level
    user.avg_xp_per_activity_ema = seed.avg_xp_per_activity_ema
    await db.flush()

    activities = (
        await db.scalars(
            select(Activity).where(Activity.user_id == user.id).order_by(Activity.start_time.asc())
        )
    ).all()

    for activity in activities:
        active_goal = await _goal_active_at(db, user.id, activity.start_time)

        course_result = await course_service.process_activity_course(db, user, activity)
        calculator.process_activity(db, user, activity, course_result.difficulty_rating, active_goal)
        await skills.process_activity_skills(db, user, activity)
        await db.flush()
