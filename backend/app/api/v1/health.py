from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.db.session import check_database
from app.schemas.api import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(
        app=settings.app_name, version=settings.app_version, environment=settings.environment,
        database=check_database(settings.database_url),  # type: ignore[arg-type]
        ai_assistance="enabled" if settings.ai_enabled else "fallback_only",
        time=datetime.now(timezone.utc),
    )
