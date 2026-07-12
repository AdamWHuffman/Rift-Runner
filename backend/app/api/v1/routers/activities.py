from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.activity import Activity
from app.models.course import Course
from app.models.region import Region
from app.models.user import User
from app.models.xp_transaction import XPTransaction
from app.schemas.activity import ActivitySummaryResponse, SkillXPResponse, XPBreakdownResponse

router = APIRouter(prefix="/activities", tags=["activities"])


@router.get("", response_model=list[ActivitySummaryResponse])
async def list_my_activities(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ActivitySummaryResponse]:
    rows = await db.execute(
        select(Activity, Course, Region)
        .outerjoin(Course, Activity.course_id == Course.id)
        .outerjoin(Region, Course.region_id == Region.id)
        .where(Activity.user_id == current_user.id)
        .order_by(Activity.start_time.desc())
        .limit(20)
    )
    activities = rows.all()
    if not activities:
        return []

    activity_ids = [activity.id for activity, _, _ in activities]
    txn_rows = await db.scalars(
        select(XPTransaction).where(XPTransaction.activity_id.in_(activity_ids))
    )
    txns_by_activity: dict = {}
    for txn in txn_rows:
        txns_by_activity.setdefault(txn.activity_id, []).append(txn)

    results = []
    for activity, course, region in activities:
        txns = txns_by_activity.get(activity.id, [])
        main_txn = next((t for t in txns if t.xp_type == "main"), None)
        skill_xp = [
            SkillXPResponse(skill_key=t.target_key, final_xp=t.final_xp)
            for t in txns
            if t.xp_type == "skill"
        ]
        results.append(
            ActivitySummaryResponse(
                id=activity.id,
                activity_name=activity.activity_name,
                activity_type=activity.activity_type,
                start_time=activity.start_time,
                distance_meters=activity.distance_meters,
                duration_seconds=activity.duration_seconds,
                elevation_gain_meters=activity.elevation_gain_meters,
                avg_hr=activity.avg_hr,
                is_personal_record=activity.is_personal_record,
                course_name=course.name if course else None,
                region_name=region.name if region else None,
                temperature_c=activity.temperature_c,
                heat_index_c=activity.heat_index_c,
                main_xp=XPBreakdownResponse(
                    base_xp=main_txn.base_xp,
                    multipliers=main_txn.multipliers,
                    final_xp=main_txn.final_xp,
                    level_before=main_txn.level_before,
                    level_after=main_txn.level_after,
                )
                if main_txn
                else None,
                skill_xp=skill_xp,
            )
        )
    return results
