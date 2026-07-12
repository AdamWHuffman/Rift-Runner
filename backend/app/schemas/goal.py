import uuid

from pydantic import BaseModel


class GoalResponse(BaseModel):
    id: uuid.UUID
    key: str
    display_name: str
    description: str
    zone_weight_targets: list[float]

    model_config = {"from_attributes": True}


class SetActiveGoalRequest(BaseModel):
    goal_key: str
