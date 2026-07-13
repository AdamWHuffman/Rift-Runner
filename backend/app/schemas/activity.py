import uuid
from datetime import datetime

from pydantic import BaseModel


class LatLon(BaseModel):
    lat: float
    lon: float


class XPBreakdownResponse(BaseModel):
    base_xp: float
    multipliers: dict[str, float]
    final_xp: float
    level_before: int
    level_after: int


class SkillXPResponse(BaseModel):
    skill_key: str
    final_xp: float


class ImportableActivityResponse(BaseModel):
    garmin_activity_id: str
    activity_name: str | None
    activity_type: str
    start_time: datetime
    distance_meters: float
    duration_seconds: float


class ImportActivitiesRequest(BaseModel):
    garmin_activity_ids: list[str]


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
    temperature_c: float | None
    heat_index_c: float | None
    main_xp: XPBreakdownResponse | None
    skill_xp: list[SkillXPResponse]
    polyline: list[LatLon]
