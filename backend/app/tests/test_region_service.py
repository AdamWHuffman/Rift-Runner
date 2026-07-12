import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.region import Region
from app.services.region_engine import geocode, region_service


async def test_get_or_create_region_creates_new_region(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(geocode, "detect_theme", lambda lat, lon: geocode.THEME_RIVERLANDS)

    region = await region_service.get_or_create_region_for_point(db_session, 38.88, -77.09, "Arlington, VA")
    await db_session.commit()

    assert region.theme == geocode.THEME_RIVERLANDS
    assert region.real_place_label == "Arlington, VA"
    assert region.name  # non-empty generated name

    all_regions = (await db_session.scalars(select(Region))).all()
    assert len(all_regions) == 1


async def test_get_or_create_region_reuses_nearby_region(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(geocode, "detect_theme", lambda lat, lon: geocode.THEME_RIVERLANDS)

    first = await region_service.get_or_create_region_for_point(db_session, 38.88, -77.09, "Arlington, VA")
    await db_session.commit()

    # ~1km away -- well within the 10km reuse radius.
    second = await region_service.get_or_create_region_for_point(db_session, 38.889, -77.09, "Nearby Place")
    await db_session.commit()

    assert second.id == first.id
    all_regions = (await db_session.scalars(select(Region))).all()
    assert len(all_regions) == 1


async def test_get_or_create_region_creates_separate_region_when_far(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(geocode, "detect_theme", lambda lat, lon: geocode.THEME_HIGHLANDS)

    first = await region_service.get_or_create_region_for_point(db_session, 38.88, -77.09, "Arlington, VA")
    await db_session.commit()

    # Far away (roughly NYC) -- should create a distinct region.
    second = await region_service.get_or_create_region_for_point(db_session, 40.71, -74.00, "New York, NY")
    await db_session.commit()

    assert second.id != first.id
    all_regions = (await db_session.scalars(select(Region))).all()
    assert len(all_regions) == 2
