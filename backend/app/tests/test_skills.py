import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import Activity
from app.models.skill import Skill
from app.models.skill_progress import SkillProgress
from app.models.user import User
from app.models.xp_transaction import XPTransaction
from app.services.xp_engine import skill_formulas, skills


async def _seed_skills(db_session: AsyncSession) -> None:
    for key, name in [
        ("speed", "Speed"),
        ("endurance", "Endurance"),
        ("health", "Health"),
        ("consistency", "Consistency"),
    ]:
        db_session.add(Skill(key=key, display_name=name))
    await db_session.commit()


def _activity(user_id: uuid.UUID, **overrides) -> Activity:
    defaults = dict(
        id=uuid.uuid4(),
        user_id=user_id,
        garmin_activity_id=str(overrides.pop("garmin_activity_id", 1)),
        source="garmin_sync",
        activity_type="running",
        start_time=datetime(2026, 7, 10, tzinfo=timezone.utc),
        duration_seconds=1800.0,
        distance_meters=5000.0,
        elevation_gain_meters=0.0,
        avg_hr=150,
        processing_status="pending",
    )
    defaults.update(overrides)
    return Activity(**defaults)


async def test_process_activity_skills_creates_progress_for_each_active_skill(
    db_session: AsyncSession, test_user: User
) -> None:
    await _seed_skills(db_session)
    activity = _activity(test_user.id)
    db_session.add(activity)
    await db_session.flush()

    await skills.process_activity_skills(db_session, test_user, activity)
    await db_session.commit()

    progress_rows = (await db_session.scalars(select(SkillProgress).where(SkillProgress.user_id == test_user.id))).all()
    assert len(progress_rows) == 4  # all seeded skills earned baseline XP on a first activity

    txns = (
        await db_session.scalars(
            select(XPTransaction).where(XPTransaction.user_id == test_user.id, XPTransaction.xp_type == "skill")
        )
    ).all()
    assert len(txns) == 4
    assert {t.target_key for t in txns} == {"speed", "endurance", "health", "consistency"}
    assert all(t.final_xp == skill_formulas.SKILL_BASE_XP for t in txns)


async def test_process_activity_skills_ignores_inactive_skills(db_session: AsyncSession, test_user: User) -> None:
    db_session.add(Skill(key="speed", display_name="Speed", is_active=False))
    await db_session.commit()
    activity = _activity(test_user.id)
    db_session.add(activity)
    await db_session.flush()

    level_ups = await skills.process_activity_skills(db_session, test_user, activity)
    await db_session.commit()

    assert level_ups == []
    progress_rows = (await db_session.scalars(select(SkillProgress).where(SkillProgress.user_id == test_user.id))).all()
    assert progress_rows == []


async def test_process_activity_skills_scopes_speed_to_same_activity_type(
    db_session: AsyncSession, test_user: User
) -> None:
    await _seed_skills(db_session)
    # A fast bike ride shouldn't count as this user's "best pace" for running.
    bike = _activity(test_user.id, garmin_activity_id=1, activity_type="cycling", duration_seconds=600.0)
    db_session.add(bike)
    await db_session.flush()
    await skills.process_activity_skills(db_session, test_user, bike)
    await db_session.commit()

    run = _activity(test_user.id, garmin_activity_id=2, activity_type="running")
    db_session.add(run)
    await db_session.flush()
    await skills.process_activity_skills(db_session, test_user, run)
    await db_session.commit()

    speed_skill = await db_session.scalar(select(Skill).where(Skill.key == "speed"))
    txn = await db_session.scalar(
        select(XPTransaction).where(XPTransaction.activity_id == run.id, XPTransaction.target_key == "speed")
    )
    assert txn is not None
    # No prior *running* history -> baseline, not compared against the cycling activity.
    assert txn.base_xp == pytest.approx(skill_formulas.SKILL_BASE_XP)


async def test_process_activity_skills_consistency_spans_all_activity_types(
    db_session: AsyncSession, test_user: User
) -> None:
    await _seed_skills(db_session)
    yesterday_bike = _activity(
        test_user.id,
        garmin_activity_id=1,
        activity_type="cycling",
        start_time=datetime(2026, 7, 9, tzinfo=timezone.utc),
    )
    db_session.add(yesterday_bike)
    await db_session.flush()
    await skills.process_activity_skills(db_session, test_user, yesterday_bike)
    await db_session.commit()

    today_run = _activity(
        test_user.id,
        garmin_activity_id=2,
        activity_type="running",
        start_time=datetime(2026, 7, 10, tzinfo=timezone.utc),
    )
    db_session.add(today_run)
    await db_session.flush()
    await skills.process_activity_skills(db_session, test_user, today_run)
    await db_session.commit()

    txn = await db_session.scalar(
        select(XPTransaction).where(XPTransaction.activity_id == today_run.id, XPTransaction.target_key == "consistency")
    )
    assert txn is not None
    # ~1 day gap since the bike ride (a different activity type) should still count.
    assert txn.base_xp == pytest.approx(skill_formulas.SKILL_BASE_XP * skill_formulas.CONSISTENCY_RATIO_CAP)


async def test_process_activity_skills_returns_level_up_when_target_cleared(
    db_session: AsyncSession, test_user: User
) -> None:
    await _seed_skills(db_session)
    speed_skill = await db_session.scalar(select(Skill).where(Skill.key == "speed"))
    assert speed_skill is not None

    # Pre-seed near the level-1 target (400) so one more baseline award (150) tips it over.
    from app.services.xp_engine import leveling

    db_session.add(
        SkillProgress(
            user_id=test_user.id,
            skill_id=speed_skill.id,
            level=1,
            xp_into_level=300.0,
            xp_to_next_level_snapshot=leveling.activities_to_next_level(1) * 80.0,
            activities_this_level=3,
            avg_xp_per_activity_ema=80.0,
        )
    )
    await db_session.commit()

    activity = _activity(test_user.id)
    db_session.add(activity)
    await db_session.flush()

    level_ups = await skills.process_activity_skills(db_session, test_user, activity)
    await db_session.commit()

    speed_level_ups = [e for e in level_ups if e.skill_key == "speed"]
    assert len(speed_level_ups) == 1
    assert speed_level_ups[0].from_level == 1
    assert speed_level_ups[0].to_level == 2
