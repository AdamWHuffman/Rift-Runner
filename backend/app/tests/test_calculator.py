import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import Activity
from app.models.goal import Goal
from app.models.user import User
from app.models.xp_transaction import XPTransaction
from app.services.xp_engine import calculator, formulas

# Precise elevation multiplier for the default _activity() fixture (60m gain
# over 5.2km) -- the plan's "1.115" worked example rounds this for readability.
ELEVATION_MULTIPLIER = 1.0 + (60.0 / 5.2) * 0.01


def _activity(user_id: uuid.UUID, **overrides) -> Activity:
    defaults = dict(
        id=uuid.uuid4(),
        user_id=user_id,
        garmin_activity_id=str(overrides.pop("garmin_activity_id", 1)),
        source="garmin_sync",
        activity_type="running",
        start_time=datetime.now(timezone.utc),
        duration_seconds=1920.0,
        distance_meters=5200.0,
        elevation_gain_meters=60.0,
        calories=400.0,
        hr_seconds_in_zone={"1": 180, "2": 900, "3": 780, "4": 60, "5": 0},
        is_personal_record=False,
        processing_status="pending",
    )
    defaults.update(overrides)
    return Activity(**defaults)


async def test_process_activity_creates_xp_transaction(db_session: AsyncSession, test_user: User) -> None:
    activity = _activity(test_user.id)
    db_session.add(activity)
    await db_session.flush()

    # base_xp = 760 (plan's worked example) * elevation ~1.115 -> final = round(760*ELEVATION_MULTIPLIER) = 848
    level_ups = calculator.process_activity(db_session, test_user, activity)
    await db_session.commit()

    assert len(level_ups) == 1, "848 XP clears the fresh-user level-1 target of 5*80=400"

    txn = await db_session.scalar(select(XPTransaction).where(XPTransaction.activity_id == activity.id))
    assert txn is not None
    assert txn.xp_type == "main"
    assert txn.target_key == "main"
    assert txn.base_xp == pytest.approx(760.0)
    assert txn.multipliers["elevation"] == pytest.approx(ELEVATION_MULTIPLIER)
    assert txn.multipliers["pr_bonus"] == pytest.approx(1.0)
    assert txn.final_xp == round(760.0 * ELEVATION_MULTIPLIER)
    assert txn.level_before == 1
    assert txn.level_after == 2
    assert txn.formula_version == 1


async def test_process_activity_updates_user_leveling_state(db_session: AsyncSession, test_user: User) -> None:
    activity = _activity(test_user.id)
    db_session.add(activity)
    await db_session.flush()

    calculator.process_activity(db_session, test_user, activity)
    await db_session.commit()

    final_xp = round(760.0 * ELEVATION_MULTIPLIER)  # 848
    assert test_user.main_xp_total == pytest.approx(final_xp)
    assert test_user.main_level == 2
    assert test_user.xp_into_level == pytest.approx(final_xp - 400.0)  # 400 = 5 * initial ema of 80
    assert test_user.activities_this_level == 0


async def test_process_activity_stays_at_level_one_below_target(db_session: AsyncSession, test_user: User) -> None:
    # A modest walk that shouldn't clear the fresh-user 400 XP target.
    activity = _activity(
        test_user.id,
        garmin_activity_id=2,
        hr_seconds_in_zone={"1": 300, "2": 300, "3": 0, "4": 0, "5": 0},
        elevation_gain_meters=0.0,
    )
    db_session.add(activity)
    await db_session.flush()

    level_ups = calculator.process_activity(db_session, test_user, activity)
    await db_session.commit()

    assert level_ups == []
    assert test_user.main_level == 1
    assert test_user.activities_this_level == 1


async def test_process_activity_uses_fallback_xp_without_hr_data(db_session: AsyncSession, test_user: User) -> None:
    activity = _activity(test_user.id, garmin_activity_id=3, hr_seconds_in_zone=None, calories=300.0)
    db_session.add(activity)
    await db_session.flush()

    calculator.process_activity(db_session, test_user, activity)
    await db_session.commit()

    txn = await db_session.scalar(select(XPTransaction).where(XPTransaction.activity_id == activity.id))
    assert txn is not None
    expected_base = 300.0 * 0.5 + (1920.0 / 60.0) * 1.5
    assert txn.base_xp == pytest.approx(expected_base)


async def test_process_activity_applies_pr_bonus(db_session: AsyncSession, test_user: User) -> None:
    activity = _activity(test_user.id, garmin_activity_id=4, is_personal_record=True)
    db_session.add(activity)
    await db_session.flush()

    calculator.process_activity(db_session, test_user, activity)
    await db_session.commit()

    txn = await db_session.scalar(select(XPTransaction).where(XPTransaction.activity_id == activity.id))
    assert txn is not None
    assert txn.multipliers["pr_bonus"] == pytest.approx(1.5)
    assert txn.final_xp == round(760.0 * ELEVATION_MULTIPLIER * 1.5)


async def test_process_activity_applies_active_goal_alignment(db_session: AsyncSession, test_user: User) -> None:
    goal = Goal(
        key="base_building",
        display_name="Base Building",
        description="test",
        zone_weight_targets=[0.20, 0.35, 0.30, 0.10, 0.05],
    )
    db_session.add(goal)
    await db_session.flush()

    activity = _activity(test_user.id, garmin_activity_id=5)
    db_session.add(activity)
    await db_session.flush()

    calculator.process_activity(db_session, test_user, activity, active_goal=goal)
    await db_session.commit()

    txn = await db_session.scalar(select(XPTransaction).where(XPTransaction.activity_id == activity.id))
    assert txn is not None
    expected = formulas.goal_alignment_multiplier(activity.hr_seconds_in_zone, goal.zone_weight_targets)
    assert txn.multipliers["goal_alignment"] == pytest.approx(expected)
    assert txn.goal_id_at_time == goal.id


async def test_process_activity_goal_alignment_neutral_without_active_goal(
    db_session: AsyncSession, test_user: User
) -> None:
    activity = _activity(test_user.id, garmin_activity_id=6)
    db_session.add(activity)
    await db_session.flush()

    calculator.process_activity(db_session, test_user, activity)
    await db_session.commit()

    txn = await db_session.scalar(select(XPTransaction).where(XPTransaction.activity_id == activity.id))
    assert txn is not None
    assert txn.multipliers["goal_alignment"] == pytest.approx(1.0)
    assert txn.goal_id_at_time is None
