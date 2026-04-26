from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.application import ApplicationStatus


class ApplicationCreateRequest(BaseModel):
    job_id: int
    cover_letter: str | None = Field(default=None)


class ApplicationOut(BaseModel):
    id: int
    job_id: int
    candidate_user_id: int
    cover_letter: str | None
    status: ApplicationStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
