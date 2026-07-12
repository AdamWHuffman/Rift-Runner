import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import Activity
from app.models.garmin_credentials import GarminCredentials
from app.models.sync_job import SyncJob
from app.models.user import User
from app.models.xp_transaction import XPTransaction
from app.services.garmin_sync import adapter, sync_service

SAMPLE_ACTIVITY = {
    "activityId": 111,
    "activityType": {"typeKey": "running"},
    "startTimeGMT": "2026-07-10 11:15:00",
    "duration": 1800.0,
    "distance": 5000.0,
    "elevationGain": 20.0,
    "averageHR": 140,
    "maxHR": 160,
    "calories": 350.0,
}


async def _make_job(db_session: AsyncSession, user: User) -> SyncJob:
    job = SyncJob(user_id=user.id, status="queued")
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job


async def _make_credentials(db_session: AsyncSession, user: User) -> GarminCredentials:
    creds = GarminCredentials(user_id=user.id, encrypted_tokens="fake-encrypted-blob", status="connected")
    db_session.add(creds)
    await db_session.commit()
    await db_session.refresh(creds)
    return creds


def _patch_happy_path(monkeypatch: pytest.MonkeyPatch, activities: list[dict]) -> None:
    monkeypatch.setattr(sync_service, "decrypt", lambda blob: blob)
    monkeypatch.setattr(adapter, "deserialize_tokens", lambda blob: {})
    monkeypatch.setattr(adapter, "resume", lambda tokens: object())
    monkeypatch.setattr(adapter, "fetch_activities_since", lambda client, since: activities)


async def test_run_sync_fails_without_credentials(db_session: AsyncSession, test_user: User) -> None:
    job = await _make_job(db_session, test_user)

    result = await sync_service.run_sync(db_session, job.id, test_user.id)

    assert result.status == "failed"
    assert result.error_message is not None
    assert "not connected" in result.error_message


async def test_run_sync_creates_activities(
    db_session: AsyncSession, test_user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    creds = await _make_credentials(db_session, test_user)
    job = await _make_job(db_session, test_user)
    _patch_happy_path(monkeypatch, [SAMPLE_ACTIVITY])

    result = await sync_service.run_sync(db_session, job.id, test_user.id)

    assert result.status == "complete"
    assert result.activities_synced_count == 1

    activities = (await db_session.scalars(select(Activity).where(Activity.user_id == test_user.id))).all()
    assert len(activities) == 1
    assert activities[0].garmin_activity_id == "111"
    assert activities[0].source == "garmin_sync"

    await db_session.refresh(creds)
    assert creds.status == "connected"
    assert creds.last_sync_success_at is not None

    assert result.new_activity_ids == [str(activities[0].id)]


async def test_run_sync_processes_xp_for_new_activities(
    db_session: AsyncSession, test_user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _make_credentials(db_session, test_user)
    job = await _make_job(db_session, test_user)
    _patch_happy_path(monkeypatch, [SAMPLE_ACTIVITY])

    await sync_service.run_sync(db_session, job.id, test_user.id)

    activity = await db_session.scalar(select(Activity).where(Activity.user_id == test_user.id))
    assert activity is not None

    txn = await db_session.scalar(select(XPTransaction).where(XPTransaction.activity_id == activity.id))
    assert txn is not None
    assert txn.xp_type == "main"
    # SAMPLE_ACTIVITY has no HR-zone data -> calories/duration fallback:
    # 350*0.5 + 30*1.5 = 220, elevation 20m/5km -> 4 m/km -> *1.04
    assert txn.base_xp == pytest.approx(220.0)
    assert txn.final_xp == round(220.0 * 1.04)

    await db_session.refresh(test_user)
    assert test_user.main_xp_total == pytest.approx(txn.final_xp)


async def test_run_sync_records_level_up_events_on_job(
    db_session: AsyncSession, test_user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _make_credentials(db_session, test_user)
    job = await _make_job(db_session, test_user)
    big_activity = {**SAMPLE_ACTIVITY, "calories": 2000.0, "duration": 3600.0}
    _patch_happy_path(monkeypatch, [big_activity])

    result = await sync_service.run_sync(db_session, job.id, test_user.id)

    assert result.level_up_events is not None
    assert len(result.level_up_events) == 1
    assert result.level_up_events[0] == {"type": "main", "from_level": 1, "to_level": 2}

    await db_session.refresh(test_user)
    assert test_user.main_level == 2


async def test_run_sync_is_idempotent_on_rerun(
    db_session: AsyncSession, test_user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _make_credentials(db_session, test_user)
    _patch_happy_path(monkeypatch, [SAMPLE_ACTIVITY])

    job1 = await _make_job(db_session, test_user)
    result1 = await sync_service.run_sync(db_session, job1.id, test_user.id)
    assert result1.activities_synced_count == 1

    job2 = await _make_job(db_session, test_user)
    result2 = await sync_service.run_sync(db_session, job2.id, test_user.id)
    assert result2.activities_synced_count == 0
    assert result2.new_activity_ids == []

    activities = (await db_session.scalars(select(Activity).where(Activity.user_id == test_user.id))).all()
    assert len(activities) == 1


async def test_run_sync_cold_start_uses_most_recent_activity_when_user_has_none(
    db_session: AsyncSession, test_user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _make_credentials(db_session, test_user)
    job = await _make_job(db_session, test_user)

    monkeypatch.setattr(sync_service, "decrypt", lambda blob: blob)
    monkeypatch.setattr(adapter, "deserialize_tokens", lambda blob: {})
    monkeypatch.setattr(adapter, "resume", lambda tokens: object())

    older = {**SAMPLE_ACTIVITY, "activityId": 200, "startTimeGMT": "2026-05-01 09:00:00"}
    newer = {**SAMPLE_ACTIVITY, "activityId": 201, "startTimeGMT": "2026-06-15 09:00:00"}

    calls: list[object] = []

    def fake_fetch(client: object, since: object) -> list[dict]:
        calls.append(since)
        if len(calls) == 1:
            return []  # normal watermark-based window finds nothing new
        return [older, newer]  # wide cold-start fallback finds candidates

    monkeypatch.setattr(adapter, "fetch_activities_since", fake_fetch)

    result = await sync_service.run_sync(db_session, job.id, test_user.id)

    assert result.status == "complete"
    assert result.activities_synced_count == 1
    assert len(calls) == 2

    activities = (await db_session.scalars(select(Activity).where(Activity.user_id == test_user.id))).all()
    assert len(activities) == 1
    assert activities[0].garmin_activity_id == "201"


async def test_run_sync_no_cold_start_fallback_once_user_has_activities(
    db_session: AsyncSession, test_user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _make_credentials(db_session, test_user)
    _patch_happy_path(monkeypatch, [SAMPLE_ACTIVITY])
    job1 = await _make_job(db_session, test_user)
    await sync_service.run_sync(db_session, job1.id, test_user.id)

    calls: list[object] = []

    def fake_fetch(client: object, since: object) -> list[dict]:
        calls.append(since)
        return []

    monkeypatch.setattr(adapter, "fetch_activities_since", fake_fetch)

    job2 = await _make_job(db_session, test_user)
    result2 = await sync_service.run_sync(db_session, job2.id, test_user.id)

    assert result2.activities_synced_count == 0
    assert len(calls) == 1  # only the normal since-based call -- no fallback triggered


async def test_run_sync_marks_needs_reauth_on_auth_error(
    db_session: AsyncSession, test_user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    creds = await _make_credentials(db_session, test_user)
    job = await _make_job(db_session, test_user)

    monkeypatch.setattr(sync_service, "decrypt", lambda blob: blob)
    monkeypatch.setattr(adapter, "deserialize_tokens", lambda blob: {})

    def raise_auth_error(tokens: dict) -> None:
        raise adapter.GarminAuthError("session expired")

    monkeypatch.setattr(adapter, "resume", raise_auth_error)

    result = await sync_service.run_sync(db_session, job.id, test_user.id)

    assert result.status == "failed"
    await db_session.refresh(creds)
    assert creds.status == "needs_reauth"


async def test_run_sync_marks_error_on_fetch_failure(
    db_session: AsyncSession, test_user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    creds = await _make_credentials(db_session, test_user)
    job = await _make_job(db_session, test_user)

    monkeypatch.setattr(sync_service, "decrypt", lambda blob: blob)
    monkeypatch.setattr(adapter, "deserialize_tokens", lambda blob: {})
    monkeypatch.setattr(adapter, "resume", lambda tokens: object())

    def raise_sync_error(client: object, since: object) -> None:
        raise adapter.GarminSyncError("rate limited")

    monkeypatch.setattr(adapter, "fetch_activities_since", raise_sync_error)

    result = await sync_service.run_sync(db_session, job.id, test_user.id)

    assert result.status == "failed"
    await db_session.refresh(creds)
    assert creds.status == "error"
