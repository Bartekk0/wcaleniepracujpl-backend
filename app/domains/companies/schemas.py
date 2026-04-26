from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CompanyCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    website_url: str | None = Field(default=None, max_length=500)
    location: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None)


class CompanyOut(BaseModel):
    id: int
    owner_user_id: int
    name: str
    website_url: str | None
    location: str | None
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
