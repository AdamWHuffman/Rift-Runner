import uuid

from pydantic import BaseModel


class CourseProgressResponse(BaseModel):
    course_id: uuid.UUID
    name: str
    activity_type: str
    region_name: str
    region_theme: str
    distance_meters: float
    elevation_gain_meters: float
    difficulty_rating: int
    level: int
    xp_into_level: float
    xp_to_next_level_snapshot: float
    times_run: int
    best_time_seconds: float | None
