import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str = Field(min_length=1, max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    display_name: str
    units: str
    timezone: str
    main_level: int
    main_xp_total: float
    xp_into_level: float
    xp_to_next_level_snapshot: float
    activities_this_level: int
    onboarding_completed_at: datetime | None

    model_config = {"from_attributes": True}
