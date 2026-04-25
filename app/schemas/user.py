from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.user import UserRole


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str | None
    role: UserRole
    is_activated: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
