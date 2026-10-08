from fastapi import APIRouter, Request

from app.models.business import Business, BusinessSearchRequest
from app.services.business_search import search_mock_businesses

router = APIRouter(prefix="/businesses", tags=["Businesses"])


@router.post(
    "/search",
    response_model=list[Business],
    summary="Search med spa businesses",
    description=(
        "Returns mock fixtures, not real business listings. Supports med spa, med spas, "
        "medspa, and medspas (case-insensitive). Other industries return an empty list. "
        "Location labels the mock addresses; it does not perform a geographic search. "
        "Missing business details are null. Set source=google_places for real provider discovery."
    ),
)
async def search_businesses(body: BusinessSearchRequest, request: Request) -> list[Business]:
    if body.source == "google_places":
        return await request.app.state.gateway.discover(body)
    return search_mock_businesses(body)[:body.limit]
