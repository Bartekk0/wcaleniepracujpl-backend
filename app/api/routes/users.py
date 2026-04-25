from datetime import UTC, datetime

from fastapi import APIRouter

from app.models.user import UserRole
from app.schemas.user import UserOut

router = APIRouter()


@router.get("/me", response_model=UserOut)
def read_me() -> UserOut:
    return UserOut(
        id=0,
        email="todo@example.com",
        full_name=None,
        role=UserRole.CANDIDATE,
        is_activated=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
