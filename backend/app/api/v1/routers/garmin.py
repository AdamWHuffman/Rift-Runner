from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.crypto import encrypt
from app.db.session import get_db
from app.models.garmin_credentials import GarminCredentials
from app.models.user import User
from app.schemas.garmin import (
    GarminConnectRequest,
    GarminConnectResponse,
    GarminMfaRequest,
    GarminStatusResponse,
)
from app.services.garmin_sync import adapter

router = APIRouter(prefix="/garmin", tags=["garmin"])


@router.post("/connect", response_model=GarminConnectResponse)
async def connect_garmin(
    payload: GarminConnectRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GarminConnectResponse:
    try:
        tokens = adapter.connect(payload.email, payload.password)
    except adapter.GarminMfaRequiredError as exc:
        return GarminConnectResponse(mfa_required=True, mfa_session_id=exc.mfa_session_id)
    except adapter.GarminAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Could not log in to Garmin: {exc}"
        ) from exc

    return await _store_tokens(db, current_user, tokens)


@router.post("/connect/mfa", response_model=GarminConnectResponse)
async def complete_garmin_mfa(
    payload: GarminMfaRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GarminConnectResponse:
    try:
        tokens = adapter.complete_mfa(payload.mfa_session_id, payload.code)
    except adapter.GarminAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Could not complete Garmin MFA: {exc}"
        ) from exc

    return await _store_tokens(db, current_user, tokens)


@router.get("/status", response_model=GarminStatusResponse)
async def garmin_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GarminStatusResponse:
    creds = await db.scalar(select(GarminCredentials).where(GarminCredentials.user_id == current_user.id))
    if creds is None:
        return GarminStatusResponse(connected=False)
    return GarminStatusResponse(connected=True, status=creds.status, last_sync_success_at=creds.last_sync_success_at)


async def _store_tokens(db: AsyncSession, user: User, tokens: dict[str, str]) -> GarminConnectResponse:
    encrypted = encrypt(adapter.serialize_tokens(tokens))

    creds = await db.scalar(select(GarminCredentials).where(GarminCredentials.user_id == user.id))
    if creds is None:
        creds = GarminCredentials(user_id=user.id, encrypted_tokens=encrypted, status="connected")
        db.add(creds)
    else:
        creds.encrypted_tokens = encrypted
        creds.status = "connected"

    await db.commit()
    return GarminConnectResponse(connected=True, status=creds.status)
