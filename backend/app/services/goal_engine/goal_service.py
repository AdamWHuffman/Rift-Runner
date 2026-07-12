"""Setting a user's active goal, with history tracking so a later switch
never retroactively changes what past xp_transactions meant."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.goal import Goal
from app.models.user import User
from app.models.user_goal_history import UserGoalHistory


async def set_active_goal(db: AsyncSession, user: User, goal_key: str) -> Goal:
    goal = await db.scalar(select(Goal).where(Goal.key == goal_key, Goal.is_active.is_(True)))
    if goal is None:
        raise ValueError(f"Unknown goal key: {goal_key}")

    now = datetime.now(timezone.utc)

    if user.active_goal_id is not None:
        open_history = await db.scalar(
            select(UserGoalHistory).where(
                UserGoalHistory.user_id == user.id,
                UserGoalHistory.goal_id == user.active_goal_id,
                UserGoalHistory.deactivated_at.is_(None),
            )
        )
        if open_history is not None:
            open_history.deactivated_at = now

    db.add(UserGoalHistory(user_id=user.id, goal_id=goal.id, activated_at=now))
    user.active_goal_id = goal.id

    return goal
