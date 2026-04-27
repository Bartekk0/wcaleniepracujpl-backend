from sqlalchemy.orm import Session

from app.domains.admin.constants import (
    JOB_APPROVED_AUDIT_ACTION,
    JOB_AUDIT_TARGET_TYPE,
    JOB_REJECTED_AUDIT_ACTION,
)
from app.domains.admin.repository import (
    create_admin_audit_log,
    get_job_for_moderation,
    list_pending_moderation_jobs,
    set_job_moderation_result,
)
from app.models.admin_audit_log import AdminAuditLog
from app.models.job import Job, JobModerationStatus


def get_moderation_queue(db: Session) -> list[Job]:
    return list_pending_moderation_jobs(db)


def approve_job(
    db: Session,
    *,
    admin_user_id: int,
    job_id: int,
    note: str | None,
) -> tuple[Job, AdminAuditLog]:
    return _moderate_job(
        db,
        admin_user_id=admin_user_id,
        job_id=job_id,
        note=note,
        status=JobModerationStatus.APPROVED,
        action=JOB_APPROVED_AUDIT_ACTION,
    )


def reject_job(
    db: Session,
    *,
    admin_user_id: int,
    job_id: int,
    note: str | None,
) -> tuple[Job, AdminAuditLog]:
    return _moderate_job(
        db,
        admin_user_id=admin_user_id,
        job_id=job_id,
        note=note,
        status=JobModerationStatus.REJECTED,
        action=JOB_REJECTED_AUDIT_ACTION,
    )


def _moderate_job(
    db: Session,
    *,
    admin_user_id: int,
    job_id: int,
    note: str | None,
    status: JobModerationStatus,
    action: str,
) -> tuple[Job, AdminAuditLog]:
    job = get_job_for_moderation(db, job_id=job_id, for_update=True)
    if job is None:
        raise ValueError("Job not found.")
    if job.moderation_status != JobModerationStatus.PENDING:
        raise ValueError("Job is already moderated.")

    set_job_moderation_result(
        db,
        job=job,
        status=status,
        admin_user_id=admin_user_id,
        note=note,
    )
    audit_log = create_admin_audit_log(
        db,
        admin_user_id=admin_user_id,
        action=action,
        target_type=JOB_AUDIT_TARGET_TYPE,
        target_id=job.id,
        note=note,
    )
    db.commit()
    db.refresh(job)
    db.refresh(audit_log)
    return job, audit_log
