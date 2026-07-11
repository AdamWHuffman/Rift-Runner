import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt
from app.models.activity import Activity
from app.models.garmin_credentials import GarminCredentials
from app.models.sync_job import SyncJob
from app.services.garmin_sync import adapter, mapper

SYNC_OVERLAP = timedelta(hours=2)
DEFAULT_LOOKBACK = timedelta(days=30)


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

    synced_count = 0
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
        db.add(Activity(user_id=user_id, source="garmin_sync", **fields))
        synced_count += 1

    creds.status = "connected"
    creds.last_sync_success_at = datetime.now(timezone.utc)
    job.status = "complete"
    job.activities_synced_count = synced_count
    job.finished_at = datetime.now(timezone.utc)
    await db.commit()
    return job


async def _fail(db: AsyncSession, job: SyncJob, message: str) -> SyncJob:
    job.status = "failed"
    job.error_message = message
    job.finished_at = datetime.now(timezone.utc)
    await db.commit()
    return job
