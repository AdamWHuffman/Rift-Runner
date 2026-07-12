from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.region import Region
from app.models.user import User
from app.schemas.region import AddressSuggestionResponse, HomeBaseRequest, RegionResponse
from app.services.region_engine import geocode, region_service

router = APIRouter(prefix="/regions", tags=["regions"])


@router.get("/geocode-suggestions", response_model=list[AddressSuggestionResponse])
async def geocode_suggestions(
    q: str,
    current_user: User = Depends(get_current_user),
) -> list[AddressSuggestionResponse]:
    if len(q.strip()) < 3:
        return []
    results = geocode.search_addresses(q)
    return [AddressSuggestionResponse(display_name=r.display_name, lat=r.lat, lon=r.lon) for r in results]


@router.post("/home-base", response_model=RegionResponse)
async def set_home_base(
    payload: HomeBaseRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RegionResponse:
    geo = geocode.geocode_address(payload.address)
    if geo is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not find that address")

    region = await region_service.get_or_create_region_for_point(db, geo.lat, geo.lon, geo.display_name)
    current_user.home_region_id = region.id
    current_user.units = "imperial" if geocode.is_likely_united_states(geo.lat, geo.lon) else "metric"
    await db.commit()
    return RegionResponse.model_validate(region)


@router.get("/home-base", response_model=RegionResponse | None)
async def get_home_base(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RegionResponse | None:
    if current_user.home_region_id is None:
        return None
    region = await db.get(Region, current_user.home_region_id)
    return RegionResponse.model_validate(region) if region else None
