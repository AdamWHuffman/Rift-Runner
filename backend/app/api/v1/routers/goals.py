from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.goal import Goal
from app.models.user import User
from app.schemas.goal import GoalResponse, SetActiveGoalRequest
from app.services.goal_engine import goal_service

router = APIRouter(prefix="/goals", tags=["goals"])


@router.get("", response_model=list[GoalResponse])
async def list_goals(db: AsyncSession = Depends(get_db)) -> list[GoalResponse]:
    goals = (await db.scalars(select(Goal).where(Goal.is_active.is_(True)))).all()
    return [GoalResponse.model_validate(g) for g in goals]


@router.get("/active", response_model=GoalResponse | None)
async def get_active_goal(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GoalResponse | None:
    if current_user.active_goal_id is None:
        return None
    goal = await db.get(Goal, current_user.active_goal_id)
    return GoalResponse.model_validate(goal) if goal else None


@router.post("/active", response_model=GoalResponse)
async def set_active_goal(
    payload: SetActiveGoalRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GoalResponse:
    try:
        goal = await goal_service.set_active_goal(db, current_user, payload.goal_key)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await db.commit()
    return GoalResponse.model_validate(goal)
