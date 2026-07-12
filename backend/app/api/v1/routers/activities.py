import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.crypto import decrypt
from app.db.session import get_db
from app.models.activity import Activity
from app.models.course_activity_link import CourseActivityLink
from app.models.garmin_credentials import GarminCredentials
from app.models.user import User
from app.models.xp_transaction import XPTransaction
from app.schemas.activity import (
    ActivitySummaryResponse,
    ImportableActivityResponse,
    ImportActivitiesRequest,
)
from app.schemas.auth import UserResponse
from app.services import activity_view
from app.services.account import recalculate_service
from app.services.garmin_sync import adapter, mapper, sync_service

router = APIRouter(prefix="/activities", tags=["activities"])


async def _resume_garmin_client(db: AsyncSession, user_id: uuid.UUID):
    creds = await db.scalar(select(GarminCredentials).where(GarminCredentials.user_id == user_id))
    if creds is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Garmin account is not connected")
    try:
        tokens = adapter.deserialize_tokens(decrypt(creds.encrypted_tokens))
        return adapter.resume(tokens)
    except adapter.GarminAuthError as exc:
        creds.status = "needs_reauth"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Garmin session expired, reconnect required"
        ) from exc


@router.get("", response_model=list[ActivitySummaryResponse])
async def list_my_activities(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ActivitySummaryResponse]:
    return await activity_view.list_activity_summaries(db, current_user.id, limit=min(limit, 500))


@router.get("/importable", response_model=list[ImportableActivityResponse])
async def list_importable_activities(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ImportableActivityResponse]:
    """Activities Garmin has on record, from a few weeks before this account
    was created through now, that aren't already synced locally -- lets a
    user backfill activities from before they connected the app."""
    client = await _resume_garmin_client(db, current_user.id)
    since = current_user.created_at - sync_service.IMPORT_LOOKBACK

    try:
        raw_activities = adapter.fetch_activities_since(client, since.date())
    except adapter.GarminSyncError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    existing_ids = set(
        await db.scalars(select(Activity.garmin_activity_id).where(Activity.user_id == current_user.id))
    )

    results: list[ImportableActivityResponse] = []
    for raw in raw_activities:
        fields = mapper.map_activity(raw)
        garmin_id = fields["garmin_activity_id"]
        if garmin_id is None or garmin_id in existing_ids:
            continue
        results.append(
            ImportableActivityResponse(
                garmin_activity_id=garmin_id,
                activity_name=fields["activity_name"],
                activity_type=fields["activity_type"],
                start_time=fields["start_time"],
                distance_meters=fields["distance_meters"],
                duration_seconds=fields["duration_seconds"],
            )
        )
    results.sort(key=lambda r: r.start_time, reverse=True)
    return results


@router.post("/import", response_model=UserResponse)
async def import_activities(
    payload: ImportActivitiesRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    if not payload.garmin_activity_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No activities selected")

    client = await _resume_garmin_client(db, current_user.id)
    since = current_user.created_at - sync_service.IMPORT_LOOKBACK

    try:
        raw_activities = adapter.fetch_activities_since(client, since.date())
    except adapter.GarminSyncError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    wanted = set(payload.garmin_activity_ids)
    imported_count = 0
    for raw in raw_activities:
        fields = mapper.map_activity(raw)
        garmin_id = fields["garmin_activity_id"]
        if garmin_id is None or garmin_id not in wanted:
            continue

        existing = await db.scalar(
            select(Activity).where(Activity.user_id == current_user.id, Activity.garmin_activity_id == garmin_id)
        )
        if existing is not None:
            continue

        activity = sync_service.build_activity_from_fields(current_user.id, fields, client, source="manual_import")
        db.add(activity)
        imported_count += 1

    if imported_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="None of the selected activities could be imported"
        )

    await db.flush()
    # A newly-imported activity can land anywhere in the timeline (that's
    # the whole point of backfilling), so there's no way to correctly
    # patch in just its XP incrementally -- rebuild everything from the
    # full, now-updated activity set instead.
    await recalculate_service.recalculate_all(db, current_user)
    await db.commit()
    await db.refresh(current_user)
    return UserResponse.model_validate(current_user)


@router.delete("/{activity_id}", response_model=UserResponse)
async def delete_activity(
    activity_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    activity = await db.get(Activity, activity_id)
    if activity is None or activity.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found")

    # Clear this one activity's own FK references before deleting it --
    # recalculate_all rebuilds the rest of the user's derived state (and
    # re-wipes/re-derives everyone else's xp_transactions/course links)
    # right after anyway.
    await db.execute(delete(XPTransaction).where(XPTransaction.activity_id == activity_id))
    await db.execute(delete(CourseActivityLink).where(CourseActivityLink.activity_id == activity_id))
    await db.delete(activity)
    await db.flush()

    await recalculate_service.recalculate_all(db, current_user)
    await db.commit()
    await db.refresh(current_user)
    return UserResponse.model_validate(current_user)
