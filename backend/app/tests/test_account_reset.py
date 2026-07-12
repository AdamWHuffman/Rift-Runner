import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import Activity
from app.models.course import Course
from app.models.course_activity_link import CourseActivityLink
from app.models.course_user_progress import CourseUserProgress
from app.models.region import Region
from app.models.skill import Skill
from app.models.skill_progress import SkillProgress
from app.models.user import User
from app.models.xp_transaction import XPTransaction
from app.services.account import reset_service
from app.services.xp_engine import leveling


async def _seed_full_progression(db_session: AsyncSession, user: User) -> Course:
    region = Region(
        name="The Millrace Reaches", theme="riverlands", centroid_lat=38.88, centroid_lon=-77.09,
        real_place_label="test region",
    )
    db_session.add(region)
    await db_session.flush()

    course = Course(
        region_id=region.id, activity_type="running", name="Test Loop",
        canonical_polyline=[{"lat": 38.88, "lon": -77.09}, {"lat": 38.89, "lon": -77.10}],
        start_geohash="abcdefg", end_geohash="abcdefh",
        distance_meters=5000.0, elevation_gain_meters=20.0, discovery_count=1,
    )
    db_session.add(course)
    await db_session.flush()

    activity = Activity(
        id=uuid.uuid4(), user_id=user.id, garmin_activity_id="111", source="garmin_sync",
        activity_type="running", start_time=datetime(2026, 7, 10, tzinfo=timezone.utc),
        duration_seconds=1800.0, distance_meters=5000.0, elevation_gain_meters=20.0,
        course_id=course.id, processing_status="processed",
    )
    db_session.add(activity)
    await db_session.flush()

    db_session.add(CourseActivityLink(course_id=course.id, activity_id=activity.id, similarity_score=1.0))

    seed = leveling.initial_state()
    db_session.add(
        CourseUserProgress(
            user_id=user.id, course_id=course.id, difficulty_rating_at_discovery=10,
            level=seed.level, xp_into_level=seed.xp_into_level,
            xp_to_next_level_snapshot=seed.xp_to_next_level_snapshot,
            activities_this_level=seed.activities_this_level, avg_xp_per_activity_ema=seed.avg_xp_per_activity_ema,
            times_run=1,
        )
    )

    skill = await db_session.scalar(select(Skill).where(Skill.key == "endurance"))
    if skill is None:
        skill = Skill(key="endurance", display_name="Endurance")
        db_session.add(skill)
        await db_session.flush()
    db_session.add(
        SkillProgress(
            user_id=user.id, skill_id=skill.id, level=seed.level, xp_into_level=seed.xp_into_level,
            xp_to_next_level_snapshot=seed.xp_to_next_level_snapshot,
            activities_this_level=seed.activities_this_level, avg_xp_per_activity_ema=seed.avg_xp_per_activity_ema,
        )
    )

    db_session.add(
        XPTransaction(
            user_id=user.id, activity_id=activity.id, xp_type="main", target_key="main",
            base_xp=500.0, multipliers={"elevation": 1.04}, final_xp=520.0, formula_version=1,
            level_before=1, level_after=2,
        )
    )
    db_session.add(
        XPTransaction(
            user_id=user.id, activity_id=activity.id, xp_type="skill", target_key="endurance",
            base_xp=100.0, multipliers={}, final_xp=100.0, formula_version=1, level_before=1, level_after=1,
        )
    )

    user.main_level = 2
    user.main_xp_total = 520.0
    user.xp_into_level = 20.0
    user.xp_to_next_level_snapshot = 300.0
    user.activities_this_level = 1
    user.avg_xp_per_activity_ema = 200.0

    await db_session.commit()
    return course


async def test_reset_progress_clears_user_scoped_rows(db_session: AsyncSession, test_user: User) -> None:
    course = await _seed_full_progression(db_session, test_user)

    await reset_service.reset_progress(db_session, test_user)
    await db_session.commit()

    assert (await db_session.scalars(select(Activity).where(Activity.user_id == test_user.id))).all() == []
    assert (await db_session.scalars(select(XPTransaction).where(XPTransaction.user_id == test_user.id))).all() == []
    assert (
        await db_session.scalars(select(SkillProgress).where(SkillProgress.user_id == test_user.id))
    ).all() == []
    assert (
        await db_session.scalars(
            select(CourseUserProgress).where(CourseUserProgress.user_id == test_user.id)
        )
    ).all() == []
    assert (await db_session.scalars(select(CourseActivityLink))).all() == []

    # Course/Region are global/shared -- reset must not touch them.
    still_there = await db_session.get(Course, course.id)
    assert still_there is not None

    await db_session.refresh(test_user)
    seed = leveling.initial_state()
    assert test_user.main_level == seed.level
    assert test_user.main_xp_total == 0.0
    assert test_user.xp_into_level == seed.xp_into_level
    assert test_user.xp_to_next_level_snapshot == seed.xp_to_next_level_snapshot
    assert test_user.activities_this_level == seed.activities_this_level
    assert test_user.avg_xp_per_activity_ema == seed.avg_xp_per_activity_ema


async def test_reset_progress_does_not_touch_other_users(db_session: AsyncSession, test_user: User) -> None:
    other_user = User(email="other@example.com", hashed_password="not-a-real-hash", display_name="Other")
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)

    await _seed_full_progression(db_session, test_user)
    await _seed_full_progression(db_session, other_user)

    await reset_service.reset_progress(db_session, test_user)
    await db_session.commit()

    assert (await db_session.scalars(select(Activity).where(Activity.user_id == test_user.id))).all() == []
    other_activities = (
        await db_session.scalars(select(Activity).where(Activity.user_id == other_user.id))
    ).all()
    assert len(other_activities) == 1

    other_skill_progress = (
        await db_session.scalars(select(SkillProgress).where(SkillProgress.user_id == other_user.id))
    ).all()
    assert len(other_skill_progress) == 1

    await db_session.refresh(other_user)
    assert other_user.main_level == 2
