from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    """Return the API's readiness status without contacting external services."""
    settings = get_settings()
    return HealthResponse(status="ok", service=settings.app_name)
