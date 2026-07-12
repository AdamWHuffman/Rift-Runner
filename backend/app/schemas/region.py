import uuid

from pydantic import BaseModel


class HomeBaseRequest(BaseModel):
    address: str


class AddressSuggestionResponse(BaseModel):
    display_name: str
    lat: float
    lon: float


class RegionResponse(BaseModel):
    id: uuid.UUID
    name: str
    theme: str

    model_config = {"from_attributes": True}
