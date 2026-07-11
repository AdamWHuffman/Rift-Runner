from arq.connections import RedisSettings

from app.core.config import get_settings

settings = get_settings()


async def startup(ctx: dict) -> None:
    pass


async def shutdown(ctx: dict) -> None:
    pass


async def ping(ctx: dict) -> str:
    """Placeholder task so arq has at least one registered function until Phase 2 adds real jobs."""
    return "pong"


class WorkerSettings:
    functions = [ping]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
