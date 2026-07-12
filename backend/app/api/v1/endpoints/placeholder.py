# Status: planned

from fastapi import APIRouter

from app.schemas.common import PlaceholderResponse

router = APIRouter()


@router.get("/modules", response_model=PlaceholderResponse)
def planned_modules() -> PlaceholderResponse:
    return PlaceholderResponse(
        message="Business APIs can be added here as the product grows.",
        modules=["recommender", "planner", "careers", "opportunities"],
    )
