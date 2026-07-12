import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.goal import Goal
from app.models.user import User
from app.models.user_goal_history import UserGoalHistory
from app.services.goal_engine import goal_service


async def _make_goal(db_session: AsyncSession, key: str) -> Goal:
    goal = Goal(
        key=key,
        display_name=key.title(),
        description="test goal",
        zone_weight_targets=[0.2, 0.35, 0.3, 0.1, 0.05],
    )
    db_session.add(goal)
    await db_session.commit()
    await db_session.refresh(goal)
    return goal


async def test_set_active_goal_updates_user_and_creates_history(db_session: AsyncSession, test_user: User) -> None:
    goal = await _make_goal(db_session, "base_building")

    result = await goal_service.set_active_goal(db_session, test_user, "base_building")
    await db_session.commit()

    assert result.id == goal.id
    assert test_user.active_goal_id == goal.id

    history = (await db_session.scalars(select(UserGoalHistory).where(UserGoalHistory.user_id == test_user.id))).all()
    assert len(history) == 1
    assert history[0].goal_id == goal.id
    assert history[0].deactivated_at is None


async def test_set_active_goal_closes_out_previous_history_on_switch(
    db_session: AsyncSession, test_user: User
) -> None:
    await _make_goal(db_session, "base_building")
    await _make_goal(db_session, "performance_racing")

    await goal_service.set_active_goal(db_session, test_user, "base_building")
    await db_session.commit()

    await goal_service.set_active_goal(db_session, test_user, "performance_racing")
    await db_session.commit()

    history = (
        await db_session.scalars(
            select(UserGoalHistory).where(UserGoalHistory.user_id == test_user.id).order_by(UserGoalHistory.activated_at)
        )
    ).all()
    assert len(history) == 2
    assert history[0].deactivated_at is not None  # base_building closed out
    assert history[1].deactivated_at is None  # performance_racing now active


async def test_set_active_goal_raises_for_unknown_key(db_session: AsyncSession, test_user: User) -> None:
    with pytest.raises(ValueError):
        await goal_service.set_active_goal(db_session, test_user, "not-a-real-goal")
