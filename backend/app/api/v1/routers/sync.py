import uuid
from datetime import datetime, timedelta, timezone

from arq import ArqRedis
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_arq_pool, get_current_user
from app.db.session import get_db
from app.models.sync_job import SyncJob
from app.models.user import User
from app.schemas.sync import LevelUpEventResponse, SyncJobResponse
from app.services import activity_view

router = APIRouter(prefix="/sync", tags=["sync"])

DEBOUNCE_WINDOW = timedelta(minutes=2)


async def _build_response(db: AsyncSession, job: SyncJob) -> SyncJobResponse:
    new_activities = None
    if job.new_activity_ids:
        new_activities = await activity_view.list_activity_summaries(
            db, user_id=job.user_id, activity_ids=[uuid.UUID(i) for i in job.new_activity_ids]
        )
    return SyncJobResponse(
        id=job.id,
        status=job.status,
        activities_synced_count=job.activities_synced_count,
        error_message=job.error_message,
        started_at=job.started_at,
        finished_at=job.finished_at,
        level_up_events=[LevelUpEventResponse(**e) for e in job.level_up_events] if job.level_up_events else None,
        new_activities=new_activities,
    )


@router.post("/trigger", response_model=SyncJobResponse)
async def trigger_sync(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    arq_pool: ArqRedis = Depends(get_arq_pool),
) -> SyncJobResponse:
    latest = await db.scalar(
        select(SyncJob).where(SyncJob.user_id == current_user.id).order_by(SyncJob.created_at.desc()).limit(1)
    )
    if latest is not None:
        still_in_flight = latest.status in ("queued", "running")
        recently_completed = (
            latest.status == "complete"
            and latest.finished_at is not None
            and datetime.now(timezone.utc) - latest.finished_at < DEBOUNCE_WINDOW
        )
        if still_in_flight or recently_completed:
            return await _build_response(db, latest)

    job = SyncJob(user_id=current_user.id, status="queued")
    db.add(job)
    await db.commit()
    await db.refresh(job)

    await arq_pool.enqueue_job("run_garmin_sync", str(job.id), str(current_user.id))
    return await _build_response(db, job)


@router.get("/{job_id}", response_model=SyncJobResponse)
async def get_sync_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SyncJobResponse:
    job = await db.get(SyncJob, job_id)
    if job is None or job.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sync job not found")
    return await _build_response(db, job)
