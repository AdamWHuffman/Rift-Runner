import uuid
from datetime import datetime, timezone

import pytest
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
from app.services.course_engine import course_service
from app.services.region_engine import geocode
from app.services.xp_engine import leveling


def _straight_line(start_lat: float, start_lon: float, end_lat: float, end_lon: float, n: int = 50) -> list[dict]:
    return [
        {"lat": start_lat + (end_lat - start_lat) * i / (n - 1), "lon": start_lon + (end_lon - start_lon) * i / (n - 1)}
        for i in range(n)
    ]


def _activity(user_id: uuid.UUID, **overrides) -> Activity:
    polyline = overrides.pop("polyline", _straight_line(38.86, -77.05, 38.87, -77.04))
    defaults = dict(
        id=uuid.uuid4(),
        user_id=user_id,
        garmin_activity_id=str(overrides.pop("garmin_activity_id", 1)),
        source="garmin_sync",
        activity_type="running",
        activity_name="Morning Run",
        start_time=datetime(2026, 7, 10, tzinfo=timezone.utc),
        duration_seconds=1800.0,
        distance_meters=1000.0,
        elevation_gain_meters=10.0,
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


async def test_process_activity_course_creates_new_course_on_first_run(
    db_session: AsyncSession, test_user: User
) -> None:
    activity = _activity(test_user.id)
    db_session.add(activity)
    await db_session.flush()

    result = await course_service.process_activity_course(db_session, test_user, activity)
    await db_session.commit()

    assert result.is_new_discovery is True
    assert result.course is not None
    assert result.difficulty_rating is not None
    assert activity.course_id == result.course.id
    assert activity.start_geohash is not None
    assert activity.end_geohash is not None

    courses = (await db_session.scalars(select(Course))).all()
    assert len(courses) == 1
    assert courses[0].name == "Morning Run"

    links = (await db_session.scalars(select(CourseActivityLink))).all()
    assert len(links) == 1


async def test_process_activity_course_matches_repeat_run_of_same_route(
    db_session: AsyncSession, test_user: User
) -> None:
    first = _activity(test_user.id, garmin_activity_id=1)
    db_session.add(first)
    await db_session.flush()
    first_result = await course_service.process_activity_course(db_session, test_user, first)
    await db_session.commit()

    second = _activity(test_user.id, garmin_activity_id=2)  # same polyline/distance
    db_session.add(second)
    await db_session.flush()
    second_result = await course_service.process_activity_course(db_session, test_user, second)
    await db_session.commit()

    assert second_result.is_new_discovery is False
    assert second_result.course.id == first_result.course.id

    courses = (await db_session.scalars(select(Course))).all()
    assert len(courses) == 1
    assert courses[0].discovery_count == 2


async def test_process_activity_course_creates_separate_course_for_different_route(
    db_session: AsyncSession, test_user: User
) -> None:
    first = _activity(test_user.id, garmin_activity_id=1)
    db_session.add(first)
    await db_session.flush()
    await course_service.process_activity_course(db_session, test_user, first)
    await db_session.commit()

    far_route = _straight_line(40.71, -74.00, 40.72, -74.01)  # roughly NYC
    second = _activity(test_user.id, garmin_activity_id=2, polyline=far_route, start_point=far_route[0], end_point=far_route[-1])
    db_session.add(second)
    await db_session.flush()
    second_result = await course_service.process_activity_course(db_session, test_user, second)
    await db_session.commit()

    assert second_result.is_new_discovery is True
    courses = (await db_session.scalars(select(Course))).all()
    assert len(courses) == 2
    regions = (await db_session.scalars(select(Region))).all()
    assert len(regions) == 2  # far enough apart to get separate regions too


async def test_process_activity_course_no_ops_without_gps_data(db_session: AsyncSession, test_user: User) -> None:
    activity = _activity(test_user.id, polyline=None, start_point=None, end_point=None)
    db_session.add(activity)
    await db_session.flush()

    result = await course_service.process_activity_course(db_session, test_user, activity)
    await db_session.commit()

    assert result.course is None
    assert result.is_new_discovery is False
    assert result.difficulty_rating is None
    assert activity.course_id is None


async def test_process_activity_course_difficulty_uses_endurance_skill_level(
    db_session: AsyncSession, test_user: User
) -> None:
    endurance = Skill(key="endurance", display_name="Endurance")
    db_session.add(endurance)
    await db_session.flush()
    seed = leveling.initial_state(level=20)  # a highly-trained user
    db_session.add(
        SkillProgress(
            user_id=test_user.id,
            skill_id=endurance.id,
            level=seed.level,
            xp_into_level=seed.xp_into_level,
            xp_to_next_level_snapshot=seed.xp_to_next_level_snapshot,
            activities_this_level=seed.activities_this_level,
            avg_xp_per_activity_ema=seed.avg_xp_per_activity_ema,
        )
    )
    await db_session.commit()

    activity = _activity(test_user.id, distance_meters=6000.0, elevation_gain_meters=0.0)
    db_session.add(activity)
    await db_session.flush()

    result = await course_service.process_activity_course(db_session, test_user, activity)
    await db_session.commit()

    # 6000m effective distance / capacity (3000 + 20*400=11000) -> difficulty 12 (see test_difficulty.py)
    assert result.difficulty_rating == 12


async def test_process_activity_course_repeat_xp_decays_but_never_below_floor(
    db_session: AsyncSession, test_user: User
) -> None:
    activities = []
    for i in range(1, 20):
        activity = _activity(test_user.id, garmin_activity_id=i)
        db_session.add(activity)
        await db_session.flush()
        await course_service.process_activity_course(db_session, test_user, activity)
        await db_session.commit()
        activities.append(activity)

    txns = []
    for activity in activities:
        txn = await db_session.scalar(
            select(XPTransaction).where(XPTransaction.activity_id == activity.id, XPTransaction.xp_type == "course")
        )
        txns.append(txn)

    # Run 1 = 1.0x, run 5 = 0.8x, run 15+ = floored at 0.3x forever (plan's own figures).
    assert txns[0].multipliers["repeat_decay"] == pytest.approx(1.0)
    assert txns[4].multipliers["repeat_decay"] == pytest.approx(0.8)
    assert txns[14].multipliers["repeat_decay"] == pytest.approx(0.3)
    assert txns[18].multipliers["repeat_decay"] == pytest.approx(0.3)
    # Decay never goes negative or keeps shrinking past the floor.
    assert all(t.multipliers["repeat_decay"] >= 0.3 for t in txns)
