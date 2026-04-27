from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.job import JobModerationStatus
from app.models.report import ReportStatus


class ModerationDecisionRequest(BaseModel):
    note: str | None = Field(default=None, max_length=2000)


class ModerationJobOut(BaseModel):
    id: int
    company_id: int
    title: str
    location: str | None
    employment_type: str | None
    description: str
    moderation_status: JobModerationStatus
    moderation_note: str | None
    moderated_by_admin_user_id: int | None
    moderated_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminAuditLogOut(BaseModel):
    id: int
    admin_user_id: int
    action: str
    target_type: str
    target_id: int
    note: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ModerationActionResponse(BaseModel):
    job: ModerationJobOut
    audit_log: AdminAuditLogOut


class CreateReportRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=4000)


class ReportOut(BaseModel):
    id: int
    job_id: int
    reporter_user_id: int
    reason: str
    status: ReportStatus
    resolution_note: str | None
    resolved_by_admin_user_id: int | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReportDecisionRequest(BaseModel):
    note: str | None = Field(default=None, max_length=2000)


class ReportActionResponse(BaseModel):
    report: ReportOut
    audit_log: AdminAuditLogOut
