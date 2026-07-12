"""Wipes one user's progression data so they can experience the app as a
fresh user again -- distance/course/skill/level history all cleared, but the
account itself (login, Garmin connection, home base, active goal) stays put.

Courses and regions are global, shared rows (any user's activities can match
an existing course), so they're deliberately left untouched -- only this
user's own activities, XP ledger, and per-user progress rows are removed.
"""

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import Activity
from app.models.course_activity_link import CourseActivityLink
from app.models.course_user_progress import CourseUserProgress
from app.models.skill_progress import SkillProgress
from app.models.user import User
from app.models.xp_transaction import XPTransaction
from app.services.xp_engine import leveling


async def reset_progress(db: AsyncSession, user: User) -> None:
    await db.execute(delete(XPTransaction).where(XPTransaction.user_id == user.id))
    await db.execute(
        delete(CourseActivityLink).where(
            CourseActivityLink.activity_id.in_(select(Activity.id).where(Activity.user_id == user.id))
        )
    )
    await db.execute(delete(CourseUserProgress).where(CourseUserProgress.user_id == user.id))
    await db.execute(delete(SkillProgress).where(SkillProgress.user_id == user.id))
    await db.execute(delete(Activity).where(Activity.user_id == user.id))

    seed = leveling.initial_state()
    user.main_level = seed.level
    user.main_xp_total = 0.0
    user.xp_into_level = seed.xp_into_level
    user.xp_to_next_level_snapshot = seed.xp_to_next_level_snapshot
    user.activities_this_level = seed.activities_this_level
    user.avg_xp_per_activity_ema = seed.avg_xp_per_activity_ema
