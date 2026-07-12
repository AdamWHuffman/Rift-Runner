import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt
from app.models.activity import Activity
from app.models.garmin_credentials import GarminCredentials
from app.models.goal import Goal
from app.models.sync_job import SyncJob
from app.models.user import User
from app.services.course_engine import course_service
from app.services.garmin_sync import adapter, mapper
from app.services.weather import open_meteo
from app.services.xp_engine import calculator, skills

SYNC_OVERLAP = timedelta(hours=2)
DEFAULT_LOOKBACK = timedelta(days=30)
# Only used as a cold-start fallback (see below) -- deliberately much wider
# than DEFAULT_LOOKBACK since its job is to find *something* to seed from.
COLD_START_LOOKBACK = timedelta(days=365)


async def run_sync(db: AsyncSession, job_id: uuid.UUID, user_id: uuid.UUID) -> SyncJob:
    job = await db.get(SyncJob, job_id)
    assert job is not None, f"sync job {job_id} not found"

    job.status = "running"
    job.started_at = datetime.now(timezone.utc)
    await db.commit()

    creds = await db.scalar(select(GarminCredentials).where(GarminCredentials.user_id == user_id))
    if creds is None:
        return await _fail(db, job, "Garmin account is not connected")

    creds.last_sync_attempt_at = datetime.now(timezone.utc)

    try:
        tokens = adapter.deserialize_tokens(decrypt(creds.encrypted_tokens))
        client = adapter.resume(tokens)
    except adapter.GarminAuthError:
        creds.status = "needs_reauth"
        return await _fail(db, job, "Garmin session expired, reconnect required")

    since = (creds.last_sync_success_at or datetime.now(timezone.utc) - DEFAULT_LOOKBACK) - SYNC_OVERLAP

    try:
        raw_activities = adapter.fetch_activities_since(client, since.date())
    except adapter.GarminSyncError as exc:
        creds.status = "error"
        return await _fail(db, job, str(exc))

    has_local_activities = (
        await db.scalar(select(Activity.id).where(Activity.user_id == user_id).limit(1))
    ) is not None

    if not has_local_activities and not raw_activities:
        # Cold start -- most commonly right after a progress reset, where
        # creds.last_sync_success_at survives even though local activities
        # were wiped, so the normal since-cutoff above finds nothing "new"
        # even though Garmin has real history. Search much further back and
        # seed with just the single most recent activity as the new
        # baseline, rather than replaying a large amount of history at once.
        try:
            raw_activities = adapter.fetch_activities_since(
                client, (datetime.now(timezone.utc) - COLD_START_LOOKBACK).date()
            )
        except adapter.GarminSyncError as exc:
            creds.status = "error"
            return await _fail(db, job, str(exc))
        if raw_activities:
            raw_activities = [max(raw_activities, key=lambda r: r.get("startTimeGMT") or "")]

    user = await db.get(User, user_id)
    assert user is not None, f"user {user_id} not found"

    active_goal = await db.get(Goal, user.active_goal_id) if user.active_goal_id else None

    synced_count = 0
    level_up_events: list[dict] = []
    new_activity_ids: list[str] = []
    for raw in raw_activities:
        fields = mapper.map_activity(raw)
        existing = await db.scalar(
            select(Activity).where(
                Activity.user_id == user_id,
                Activity.garmin_activity_id == fields["garmin_activity_id"],
            )
        )
        if existing is not None:
            continue

        activity = Activity(id=uuid.uuid4(), user_id=user_id, source="garmin_sync", **fields)
        if fields["garmin_activity_id"] is not None:
            activity.polyline = adapter.fetch_activity_polyline(client, fields["garmin_activity_id"])
        db.add(activity)
        synced_count += 1
        new_activity_ids.append(str(activity.id))

        if activity.start_point:
            weather = open_meteo.fetch_weather_at(
                activity.start_point["lat"], activity.start_point["lon"], activity.start_time
            )
            if weather is not None:
                activity.temperature_c = weather.temperature_c
                activity.humidity_pct = weather.humidity_pct
                activity.heat_index_c = weather.heat_index_c

        course_result = await course_service.process_activity_course(db, user, activity)
        activity._is_new_course_discovery = course_result.is_new_discovery
        for event in course_result.level_ups:
            level_up_events.append(
                {
                    "type": "course",
                    "course_id": str(course_result.course.id) if course_result.course else None,
                    "course_name": course_result.course.name if course_result.course else None,
                    "from_level": event.from_level,
                    "to_level": event.to_level,
                }
            )

        for event in calculator.process_activity(db, user, activity, course_result.difficulty_rating, active_goal):
            level_up_events.append({"type": "main", "from_level": event.from_level, "to_level": event.to_level})

        for skill_event in await skills.process_activity_skills(db, user, activity):
            level_up_events.append(
                {
                    "type": "skill",
                    "skill_key": skill_event.skill_key,
                    "from_level": skill_event.from_level,
                    "to_level": skill_event.to_level,
                }
            )

    creds.status = "connected"
    creds.last_sync_success_at = datetime.now(timezone.utc)
    job.status = "complete"
    job.activities_synced_count = synced_count
    job.level_up_events = level_up_events
    job.new_activity_ids = new_activity_ids
    job.finished_at = datetime.now(timezone.utc)
    await db.commit()
    return job


async def _fail(db: AsyncSession, job: SyncJob, message: str) -> SyncJob:
    job.status = "failed"
    job.error_message = message
    job.finished_at = datetime.now(timezone.utc)
    await db.commit()
    return job
