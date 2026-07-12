import uuid
from datetime import datetime

from pydantic import BaseModel


class XPBreakdownResponse(BaseModel):
    base_xp: float
    multipliers: dict[str, float]
    final_xp: float
    level_before: int
    level_after: int


class SkillXPResponse(BaseModel):
    skill_key: str
    final_xp: float


class ActivitySummaryResponse(BaseModel):
    id: uuid.UUID
    activity_name: str | None
    activity_type: str
    start_time: datetime
    distance_meters: float
    duration_seconds: float
    elevation_gain_meters: float
    avg_hr: int | None
    is_personal_record: bool | None
    course_name: str | None
    region_name: str | None
    main_xp: XPBreakdownResponse | None
    skill_xp: list[SkillXPResponse]
