import uuid

from pydantic import BaseModel


class SkillProgressResponse(BaseModel):
    key: str
    display_name: str
    level: int
    xp_into_level: float
    xp_to_next_level_snapshot: float
    activities_this_level: int
