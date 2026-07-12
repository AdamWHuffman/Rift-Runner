import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.activity import ActivitySummaryResponse


class LevelUpEventResponse(BaseModel):
    type: str
    skill_key: str | None = None
    course_id: str | None = None
    course_name: str | None = None
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
    new_activities: list[ActivitySummaryResponse] | None = None

    model_config = {"from_attributes": True}
