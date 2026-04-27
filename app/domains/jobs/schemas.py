from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class JobCreateRequest(BaseModel):
    company_id: int
    title: str = Field(min_length=1, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    employment_type: str | None = Field(default=None, max_length=100)
    description: str = Field(min_length=1)


class JobOut(BaseModel):
    id: int
    company_id: int
    title: str
    location: str | None
    employment_type: str | None
    description: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobListQueryParams(BaseModel):
    company_id: int | None = None
    title_query: str | None = Field(default=None, min_length=1, max_length=255)
    location: str | None = Field(default=None, min_length=1, max_length=255)
    employment_type: str | None = Field(default=None, min_length=1, max_length=100)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
