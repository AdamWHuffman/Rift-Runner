import uuid
from datetime import datetime

from pydantic import BaseModel


class LevelUpEventResponse(BaseModel):
    type: str
    skill_key: str | None = None
    from_level: int
    to_level: int


class SyncJobResponse(BaseModel):
    id: uuid.UUID
    status: str
    activities_synced_count: int
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    level_up_events: list[LevelUpEventResponse] | None = None

    model_config = {"from_attributes": True}
