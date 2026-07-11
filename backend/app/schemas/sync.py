import uuid
from datetime import datetime

from pydantic import BaseModel


class SyncJobResponse(BaseModel):
    id: uuid.UUID
    status: str
    activities_synced_count: int
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None

    model_config = {"from_attributes": True}
