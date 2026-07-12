import uuid

from pydantic import BaseModel


class HomeBaseRequest(BaseModel):
    address: str


class RegionResponse(BaseModel):
    id: uuid.UUID
    name: str
    theme: str

    model_config = {"from_attributes": True}
