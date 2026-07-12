import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import Activity
from app.models.course import Course
from app.models.course_user_progress import CourseUserProgress
from app.models.goal import Goal
from app.models.skill import Skill
from app.models.skill_progress import SkillProgress
from app.models.user import User
from app.models.user_goal_history import UserGoalHistory
from app.models.xp_transaction import XPTransaction
from app.services.account import recalculate_service
from app.services.course_engine import course_service
from app.services.region_engine import geocode
from app.services.xp_engine import calculator, leveling, skills


def _straight_line(start_lat: float, start_lon: float, end_lat: float, end_lon: float, n: int = 50) -> list[dict]:
    return [
        {"lat": start_lat + (end_lat - start_lat) * i / (n - 1), "lon": start_lon + (end_lon - start_lon) * i / (n - 1)}
        for i in range(n)
    ]


def _activity(user_id: uuid.UUID, **overrides) -> Activity:
    polyline = overrides.pop("polyline", None)
    defaults = dict(
        id=uuid.uuid4(),
        user_id=user_id,
        garmin_activity_id=str(overrides.pop("garmin_activity_id", 1)),
        source="garmin_sync",
        activity_type="running",
        start_time=datetime(2026, 7, 20, tzinfo=timezone.utc),
        duration_seconds=1800.0,
        distance_meters=5000.0,
        elevation_gain_meters=0.0,
        avg_hr=150,
        polyline=polyline,
        start_point=polyline[0] if polyline else None,
        end_point=polyline[-1] if polyline else None,
        processing_status="pending",
    )
    defaults.update(overrides)
    return Activity(**defaults)


@pytest.fixture(autouse=True)
def _mock_theme(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(geocode, "detect_theme", lambda lat, lon: geocode.THEME_RIVERLANDS)


async def _seed_skills(db_session: AsyncSession) -> None:
    for key, name in [
        ("speed", "Speed"), ("endurance", "Endurance"), ("health", "Health"),
        ("consistency", "Consistency"), ("explorer", "Explorer"),
    ]:
        existing = await db_session.scalar(select(Skill).where(Skill.key == key))
        if existing is None:
            db_session.add(Skill(key=key, display_name=name))
    await db_session.commit()


async def _process_fully(db_session: AsyncSession, user: User, activity: Activity, active_goal: Goal | None = None) -> None:
    course_result = await course_service.process_activity_course(db_session, user, activity)
    calculator.process_activity(db_session, user, activity, course_result.difficulty_rating, active_goal)
    await skills.process_activity_skills(db_session, user, activity)
    await db_session.commit()


async def test_recalculate_all_matches_fresh_build_after_deleting_middle_activity(
    db_session: AsyncSession, test_user: User
) -> None:
    await _seed_skills(db_session)

    specs = [
        dict(days_ago=10, avg_hr=140),
        dict(days_ago=7, avg_hr=150),
        dict(days_ago=4, avg_hr=160),
        dict(days_ago=1, avg_hr=145),
    ]
    activities = []
    for i, spec in enumerate(specs):
        activity = _activity(
            test_user.id, garmin_activity_id=i + 1,
            start_time=datetime(2026, 7, 20, tzinfo=timezone.utc) - timedelta(days=spec["days_ago"]),
            avg_hr=spec["avg_hr"],
        )
        db_session.add(activity)
        await db_session.flush()
        await _process_fully(db_session, test_user, activity)
        activities.append(activity)

    # Delete the second-oldest activity, as the delete endpoint would.
    await db_session.delete(activities[1])
    await db_session.commit()

    await recalculate_service.recalculate_all(db_session, test_user)
    await db_session.commit()
    await db_session.refresh(test_user)

    # Independently build a second user from just the surviving specs, in
    # the same chronological order, and confirm it lands on the exact same
    # state -- proving the deleted activity's effect was fully removed, not
    # just patched around.
    fresh_user = User(email="fresh1@example.com", hashed_password="x", display_name="Fresh")
    db_session.add(fresh_user)
    await db_session.commit()
    for i, spec in enumerate([specs[0], specs[2], specs[3]]):
        clone = _activity(
            fresh_user.id, garmin_activity_id=200 + i,
            start_time=datetime(2026, 7, 20, tzinfo=timezone.utc) - timedelta(days=spec["days_ago"]),
            avg_hr=spec["avg_hr"],
        )
        db_session.add(clone)
        await db_session.flush()
        await _process_fully(db_session, fresh_user, clone)

    assert test_user.main_level == fresh_user.main_level
    assert test_user.main_xp_total == pytest.approx(fresh_user.main_xp_total)
    assert test_user.xp_into_level == pytest.approx(fresh_user.xp_into_level)
    assert test_user.activities_this_level == fresh_user.activities_this_level


async def test_recalculate_all_resets_to_defaults_with_zero_activities(
    db_session: AsyncSession, test_user: User
) -> None:
    await _seed_skills(db_session)
    activity = _activity(test_user.id, garmin_activity_id=1)
    db_session.add(activity)
    await db_session.flush()
    await _process_fully(db_session, test_user, activity)

    await db_session.delete(activity)
    await db_session.commit()

    await recalculate_service.recalculate_all(db_session, test_user)
    await db_session.commit()
    await db_session.refresh(test_user)

    seed = leveling.initial_state()
    assert test_user.main_level == seed.level
    assert test_user.main_xp_total == 0.0
    assert test_user.xp_into_level == pytest.approx(seed.xp_into_level)
    assert test_user.xp_to_next_level_snapshot == pytest.approx(seed.xp_to_next_level_snapshot)
    assert test_user.activities_this_level == seed.activities_this_level

    txns = (await db_session.scalars(select(XPTransaction).where(XPTransaction.user_id == test_user.id))).all()
    assert txns == []
    skill_rows = (await db_session.scalars(select(SkillProgress).where(SkillProgress.user_id == test_user.id))).all()
    assert skill_rows == []


async def test_recalculate_all_uses_goal_active_at_each_activitys_own_time(
    db_session: AsyncSession, test_user: User
) -> None:
    await _seed_skills(db_session)
    goal_a = Goal(key="goal_a", display_name="A", description="d", zone_weight_targets=[0.5, 0.5, 0.0, 0.0, 0.0])
    goal_b = Goal(key="goal_b", display_name="B", description="d", zone_weight_targets=[0.0, 0.0, 0.0, 0.5, 0.5])
    db_session.add_all([goal_a, goal_b])
    await db_session.flush()

    t0 = datetime(2026, 7, 1, tzinfo=timezone.utc)
    t_switch = datetime(2026, 7, 10, tzinfo=timezone.utc)
    old_activity_time = datetime(2026, 7, 5, tzinfo=timezone.utc)  # while goal_a was active
    new_activity_time = datetime(2026, 7, 15, tzinfo=timezone.utc)  # while goal_b is active

    db_session.add(UserGoalHistory(user_id=test_user.id, goal_id=goal_a.id, activated_at=t0, deactivated_at=t_switch))
    db_session.add(UserGoalHistory(user_id=test_user.id, goal_id=goal_b.id, activated_at=t_switch, deactivated_at=None))
    test_user.active_goal_id = goal_b.id
    await db_session.commit()

    a1 = _activity(test_user.id, garmin_activity_id=1, start_time=old_activity_time)
    a2 = _activity(test_user.id, garmin_activity_id=2, start_time=new_activity_time)
    db_session.add_all([a1, a2])
    await db_session.flush()
    await _process_fully(db_session, test_user, a1, active_goal=goal_a)
    await _process_fully(db_session, test_user, a2, active_goal=goal_b)

    # Flip the CURRENTLY active goal before recalculating, to prove replay
    # doesn't just naively use "whatever's active right now" for everything.
    test_user.active_goal_id = goal_a.id
    await db_session.commit()

    await recalculate_service.recalculate_all(db_session, test_user)
    await db_session.commit()

    txn1 = await db_session.scalar(
        select(XPTransaction).where(XPTransaction.activity_id == a1.id, XPTransaction.xp_type == "main")
    )
    txn2 = await db_session.scalar(
        select(XPTransaction).where(XPTransaction.activity_id == a2.id, XPTransaction.xp_type == "main")
    )
    assert txn1.goal_id_at_time == goal_a.id
    assert txn2.goal_id_at_time == goal_b.id


async def test_recalculate_all_does_not_touch_other_users(db_session: AsyncSession, test_user: User) -> None:
    await _seed_skills(db_session)
    other_user = User(email="other@example.com", hashed_password="x", display_name="Other")
    db_session.add(other_user)
    await db_session.commit()

    a1 = _activity(test_user.id, garmin_activity_id=1)
    b1 = _activity(other_user.id, garmin_activity_id=1)
    db_session.add_all([a1, b1])
    await db_session.flush()
    await _process_fully(db_session, test_user, a1)
    await _process_fully(db_session, other_user, b1)

    other_level_before = other_user.main_level
    other_xp_before = other_user.main_xp_total

    await recalculate_service.recalculate_all(db_session, test_user)
    await db_session.commit()

    await db_session.refresh(other_user)
    assert other_user.main_level == other_level_before
    assert other_user.main_xp_total == pytest.approx(other_xp_before)
    other_txns = (await db_session.scalars(select(XPTransaction).where(XPTransaction.user_id == other_user.id))).all()
    assert len(other_txns) >= 1
    other_activities = (await db_session.scalars(select(Activity).where(Activity.user_id == other_user.id))).all()
    assert len(other_activities) == 1


async def test_recalculate_all_rebuilds_course_mastery_after_deleting_a_repeat_run(
    db_session: AsyncSession, test_user: User
) -> None:
    await _seed_skills(db_session)
    polyline = _straight_line(38.86, -77.05, 38.87, -77.04)

    activities = []
    for i in range(3):
        activity = _activity(
            test_user.id, garmin_activity_id=i + 1,
            start_time=datetime(2026, 7, 20, tzinfo=timezone.utc) + timedelta(days=i),
            polyline=polyline,
        )
        db_session.add(activity)
        await db_session.flush()
        await _process_fully(db_session, test_user, activity)
        activities.append(activity)

    progress = await db_session.scalar(select(CourseUserProgress).where(CourseUserProgress.user_id == test_user.id))
    assert progress.times_run == 3

    await db_session.delete(activities[-1])  # delete the most recent repeat
    await db_session.commit()

    await recalculate_service.recalculate_all(db_session, test_user)
    await db_session.commit()

    rebuilt_progress = await db_session.scalar(
        select(CourseUserProgress).where(CourseUserProgress.user_id == test_user.id)
    )
    assert rebuilt_progress.times_run == 2

    # The global Course row itself is reused, not duplicated.
    courses = (await db_session.scalars(select(Course))).all()
    assert len(courses) == 1


async def test_recalculate_all_is_idempotent(db_session: AsyncSession, test_user: User) -> None:
    await _seed_skills(db_session)
    a1 = _activity(test_user.id, garmin_activity_id=1)
    db_session.add(a1)
    await db_session.flush()
    await _process_fully(db_session, test_user, a1)

    await recalculate_service.recalculate_all(db_session, test_user)
    await db_session.commit()
    level_1, xp_1 = test_user.main_level, test_user.main_xp_total

    await recalculate_service.recalculate_all(db_session, test_user)
    await db_session.commit()
    level_2, xp_2 = test_user.main_level, test_user.main_xp_total

    assert level_1 == level_2
    assert xp_1 == pytest.approx(xp_2)

    txns = (
        await db_session.scalars(
            select(XPTransaction).where(XPTransaction.user_id == test_user.id, XPTransaction.xp_type == "main")
        )
    ).all()
    assert len(txns) == 1  # not duplicated across the two recalculation calls


async def test_recalculate_all_correctly_reorders_a_newly_inserted_older_activity(
    db_session: AsyncSession, test_user: User
) -> None:
    await _seed_skills(db_session)
    later_time = datetime(2026, 7, 20, tzinfo=timezone.utc)
    earlier_time = datetime(2026, 7, 1, tzinfo=timezone.utc)

    # Process the "later" activity live first (as a real sync would).
    later = _activity(test_user.id, garmin_activity_id=1, start_time=later_time, avg_hr=180)
    db_session.add(later)
    await db_session.flush()
    await _process_fully(db_session, test_user, later)

    # "Import" an OLDER activity after the fact -- inserted into the table
    # without live processing, exactly like the import endpoint will do.
    earlier = _activity(test_user.id, garmin_activity_id=2, start_time=earlier_time, avg_hr=120, source="manual_import")
    db_session.add(earlier)
    await db_session.commit()

    await recalculate_service.recalculate_all(db_session, test_user)
    await db_session.commit()
    await db_session.refresh(test_user)

    # Compare against an independent, from-scratch build processed in the
    # correct chronological order (earlier first) -- proves the recalculation
    # actually replayed in start_time order rather than table/insertion order.
    fresh_user = User(email="fresh2@example.com", hashed_password="x", display_name="Fresh2")
    db_session.add(fresh_user)
    await db_session.commit()
    for garmin_id, start_time, avg_hr in [(1, earlier_time, 120), (2, later_time, 180)]:
        clone = _activity(fresh_user.id, garmin_activity_id=garmin_id, start_time=start_time, avg_hr=avg_hr)
        db_session.add(clone)
        await db_session.flush()
        await _process_fully(db_session, fresh_user, clone)

    assert test_user.main_level == fresh_user.main_level
    assert test_user.main_xp_total == pytest.approx(fresh_user.main_xp_total)
    assert test_user.activities_this_level == fresh_user.activities_this_level
