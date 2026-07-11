from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.skill import Skill
from app.models.skill_progress import SkillProgress
from app.models.user import User
from app.schemas.skill import SkillProgressResponse
from app.services.xp_engine import leveling

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("", response_model=list[SkillProgressResponse])
async def list_skill_progress(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SkillProgressResponse]:
    active_skills = (await db.scalars(select(Skill).where(Skill.is_active.is_(True)))).all()
    progress_rows = {
        p.skill_id: p
        for p in await db.scalars(select(SkillProgress).where(SkillProgress.user_id == current_user.id))
    }

    default = leveling.initial_state()
    responses = []
    for skill in active_skills:
        progress = progress_rows.get(skill.id)
        responses.append(
            SkillProgressResponse(
                key=skill.key,
                display_name=skill.display_name,
                level=progress.level if progress else default.level,
                xp_into_level=progress.xp_into_level if progress else default.xp_into_level,
                xp_to_next_level_snapshot=(
                    progress.xp_to_next_level_snapshot if progress else default.xp_to_next_level_snapshot
                ),
                activities_this_level=progress.activities_this_level if progress else default.activities_this_level,
            )
        )
    return responses
