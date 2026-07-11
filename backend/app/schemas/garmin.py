from datetime import datetime

from pydantic import BaseModel, Field


class GarminConnectRequest(BaseModel):
    email: str
    password: str = Field(min_length=1)


class GarminMfaRequest(BaseModel):
    mfa_session_id: str
    code: str = Field(min_length=1)


class GarminConnectResponse(BaseModel):
    connected: bool = False
    status: str | None = None
    mfa_required: bool = False
    mfa_session_id: str | None = None


class GarminStatusResponse(BaseModel):
    connected: bool
    status: str | None = None
    last_sync_success_at: datetime | None = None
