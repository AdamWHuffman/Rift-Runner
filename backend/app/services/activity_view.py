"""Builds ActivitySummaryResponse rows (activity + course/region + XP
breakdown) for a user -- shared by GET /activities and the sync job response
(which embeds the same shape for its newly-synced activities)."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import Activity
from app.models.course import Course
from app.models.region import Region
from app.models.xp_transaction import XPTransaction
from app.schemas.activity import ActivitySummaryResponse, SkillXPResponse, XPBreakdownResponse


async def list_activity_summaries(
    db: AsyncSession,
    user_id: uuid.UUID,
    activity_ids: list[uuid.UUID] | None = None,
    limit: int = 20,
) -> list[ActivitySummaryResponse]:
    query = (
        select(Activity, Course, Region)
        .outerjoin(Course, Activity.course_id == Course.id)
        .outerjoin(Region, Course.region_id == Region.id)
        .where(Activity.user_id == user_id)
    )
    if activity_ids is not None:
        query = query.where(Activity.id.in_(activity_ids)).order_by(Activity.start_time.asc())
    else:
        query = query.order_by(Activity.start_time.desc()).limit(limit)

    rows = await db.execute(query)
    activities = rows.all()
    if not activities:
        return []

    ids = [activity.id for activity, _, _ in activities]
    txn_rows = await db.scalars(select(XPTransaction).where(XPTransaction.activity_id.in_(ids)))
    txns_by_activity: dict = {}
    for txn in txn_rows:
        txns_by_activity.setdefault(txn.activity_id, []).append(txn)

    results = []
    for activity, course, region in activities:
        txns = txns_by_activity.get(activity.id, [])
        main_txn = next((t for t in txns if t.xp_type == "main"), None)
        skill_xp = [
            SkillXPResponse(skill_key=t.target_key, final_xp=t.final_xp) for t in txns if t.xp_type == "skill"
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
