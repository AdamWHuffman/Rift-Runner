from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.activity import ActivitySummaryResponse
from app.services import activity_view

router = APIRouter(prefix="/activities", tags=["activities"])


@router.get("", response_model=list[ActivitySummaryResponse])
async def list_my_activities(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ActivitySummaryResponse]:
    return await activity_view.list_activity_summaries(db, current_user.id)
