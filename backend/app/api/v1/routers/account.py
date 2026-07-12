from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.account import ResetAccountRequest
from app.schemas.auth import UserResponse
from app.services.account import reset_service

router = APIRouter(prefix="/account", tags=["account"])

RESET_CONFIRM_PHRASE = "RESET"


@router.post("/reset", response_model=UserResponse)
async def reset_account(
    payload: ResetAccountRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    if payload.confirm != RESET_CONFIRM_PHRASE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Type "{RESET_CONFIRM_PHRASE}" to confirm.',
        )

    await reset_service.reset_progress(db, current_user)
    await db.commit()
    await db.refresh(current_user)
    return UserResponse.model_validate(current_user)
