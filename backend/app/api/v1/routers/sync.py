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
from app.schemas.sync import SyncJobResponse

router = APIRouter(prefix="/sync", tags=["sync"])

DEBOUNCE_WINDOW = timedelta(minutes=2)


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
            return SyncJobResponse.model_validate(latest)

    job = SyncJob(user_id=current_user.id, status="queued")
    db.add(job)
    await db.commit()
    await db.refresh(job)

    await arq_pool.enqueue_job("run_garmin_sync", str(job.id), str(current_user.id))
    return SyncJobResponse.model_validate(job)


@router.get("/{job_id}", response_model=SyncJobResponse)
async def get_sync_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SyncJobResponse:
    job = await db.get(SyncJob, job_id)
    if job is None or job.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sync job not found")
    return SyncJobResponse.model_validate(job)
