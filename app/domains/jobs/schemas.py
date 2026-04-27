from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domains.jobs.tags import normalize_tag_slug

MAX_JOB_TAGS = 24


class JobCreateRequest(BaseModel):
    company_id: int
    title: str = Field(min_length=1, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    employment_type: str | None = Field(default=None, max_length=100)
    description: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: list[str]) -> list[str]:
        if len(value) > MAX_JOB_TAGS:
            raise ValueError(f"Too many tags (maximum {MAX_JOB_TAGS}).")
        seen: set[str] = set()
        normalized_order: list[str] = []
        for raw in value:
            slug = normalize_tag_slug(raw)
            if slug not in seen:
                seen.add(slug)
                normalized_order.append(raw.strip())
        return normalized_order


class JobOut(BaseModel):
    id: int
    company_id: int
    title: str
    location: str | None
    employment_type: str | None
    description: str
    tags: list[str] = Field(validation_alias="tag_slugs_list")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobListQueryParams(BaseModel):
    company_id: int | None = None
    title_query: str | None = Field(default=None, min_length=1, max_length=255)
    location: str | None = Field(default=None, min_length=1, max_length=255)
    employment_type: str | None = Field(default=None, min_length=1, max_length=100)
    tags: list[str] = Field(default_factory=list)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @field_validator("tags")
    @classmethod
    def validate_tag_filters(cls, value: list[str]) -> list[str]:
        if len(value) > MAX_JOB_TAGS:
            raise ValueError(f"Too many tags (maximum {MAX_JOB_TAGS}).")
        seen: list[str] = []
        seen_set: set[str] = set()
        for raw in value:
            slug = normalize_tag_slug(raw)
            if slug not in seen_set:
                seen_set.add(slug)
                seen.append(slug)
        return seen
