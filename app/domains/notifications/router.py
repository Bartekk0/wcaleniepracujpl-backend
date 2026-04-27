from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("/health")
def notifications_health() -> dict[str, str | bool]:
    """Lightweight readiness info for the notifications subsystem (queue dispatch gate)."""
    return {
        "status": "ok",
        "notifications_enabled": settings.notifications_enabled,
    }
