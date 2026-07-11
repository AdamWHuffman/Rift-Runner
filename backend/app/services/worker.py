import uuid

from arq.connections import RedisSettings

from app.core.config import get_settings
from app.db.session import async_session_factory
from app.services.garmin_sync import sync_service

settings = get_settings()


async def startup(ctx: dict) -> None:
    pass


async def shutdown(ctx: dict) -> None:
    pass


async def run_garmin_sync(ctx: dict, job_id: str, user_id: str) -> dict:
    async with async_session_factory() as session:
        job = await sync_service.run_sync(session, uuid.UUID(job_id), uuid.UUID(user_id))
        return {
            "job_id": str(job.id),
            "status": job.status,
            "activities_synced_count": job.activities_synced_count,
        }


class WorkerSettings:
    functions = [run_garmin_sync]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
