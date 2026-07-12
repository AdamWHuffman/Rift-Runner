from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routers import auth as auth_router
from app.api.v1.routers import courses as courses_router
from app.api.v1.routers import garmin as garmin_router
from app.api.v1.routers import goals as goals_router
from app.api.v1.routers import regions as regions_router
from app.api.v1.routers import skills as skills_router
from app.api.v1.routers import sync as sync_router
from app.core.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    app.state.arq_pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    yield
    await app.state.arq_pool.close()


app = FastAPI(title="The Quest for Health API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router, prefix="/api/v1")
app.include_router(courses_router.router, prefix="/api/v1")
app.include_router(garmin_router.router, prefix="/api/v1")
app.include_router(goals_router.router, prefix="/api/v1")
app.include_router(regions_router.router, prefix="/api/v1")
app.include_router(skills_router.router, prefix="/api/v1")
app.include_router(sync_router.router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
