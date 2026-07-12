"""Ties geocode + namegen + persistence together: find-or-create a region.

Used both for home-base setup and for auto-creating a new region when a
course is discovered outside the home region's radius -- same function,
same "is there already a nearby region" cache-or-create logic either way.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.region import Region
from app.services.geo_utils import haversine_distance_meters
from app.services.region_engine import geocode, namegen

NEARBY_REGION_RADIUS_METERS = 10_000


async def get_or_create_region_for_point(db: AsyncSession, lat: float, lon: float, real_place_label: str) -> Region:
    existing_regions = list(await db.scalars(select(Region)))
    for region in existing_regions:
        distance = haversine_distance_meters(lat, lon, region.centroid_lat, region.centroid_lon)
        if distance <= NEARBY_REGION_RADIUS_METERS:
            return region

    theme = geocode.detect_theme(lat, lon)
    name = namegen.generate_region_name(real_place_label, theme)
    region = Region(name=name, theme=theme, centroid_lat=lat, centroid_lon=lon, real_place_label=real_place_label)
    db.add(region)
    await db.flush()
    return region
