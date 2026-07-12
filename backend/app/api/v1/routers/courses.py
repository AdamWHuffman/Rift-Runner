from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.course import Course
from app.models.course_user_progress import CourseUserProgress
from app.models.region import Region
from app.models.user import User
from app.schemas.course import CourseProgressResponse

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("", response_model=list[CourseProgressResponse])
async def list_my_courses(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CourseProgressResponse]:
    rows = await db.execute(
        select(CourseUserProgress, Course, Region)
        .join(Course, CourseUserProgress.course_id == Course.id)
        .join(Region, Course.region_id == Region.id)
        .where(CourseUserProgress.user_id == current_user.id)
        .order_by(CourseUserProgress.last_run_at.desc())
    )

    return [
        CourseProgressResponse(
            course_id=course.id,
            name=course.name,
            activity_type=course.activity_type,
            region_name=region.name,
            region_theme=region.theme,
            distance_meters=course.distance_meters,
            elevation_gain_meters=course.elevation_gain_meters,
            difficulty_rating=progress.difficulty_rating_at_discovery,
            level=progress.level,
            xp_into_level=progress.xp_into_level,
            xp_to_next_level_snapshot=progress.xp_to_next_level_snapshot,
            times_run=progress.times_run,
            best_time_seconds=progress.best_time_seconds,
        )
        for progress, course, region in rows
    ]
