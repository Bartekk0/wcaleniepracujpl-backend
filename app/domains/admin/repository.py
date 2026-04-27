from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.admin_audit_log import AdminAuditLog
from app.models.job import Job, JobModerationStatus


def list_pending_moderation_jobs(db: Session) -> list[Job]:
    stmt = (
        select(Job)
        .where(Job.moderation_status == JobModerationStatus.PENDING)
        .order_by(Job.id.asc())
    )
    return list(db.execute(stmt).scalars().all())


def get_job_for_moderation(
    db: Session,
    *,
    job_id: int,
    for_update: bool = False,
) -> Job | None:
    stmt = select(Job).where(Job.id == job_id)
    if for_update:
        stmt = stmt.with_for_update()
    return db.execute(stmt).scalar_one_or_none()


def set_job_moderation_result(
    db: Session,
    *,
    job: Job,
    status: JobModerationStatus,
    admin_user_id: int,
    note: str | None,
) -> Job:
    job.moderation_status = status
    job.moderation_note = note
    job.moderated_by_admin_user_id = admin_user_id
    job.moderated_at = datetime.now(UTC)
    db.add(job)
    db.flush()
    return job


def create_admin_audit_log(
    db: Session,
    *,
    admin_user_id: int,
    action: str,
    target_type: str,
    target_id: int,
    note: str | None,
) -> AdminAuditLog:
    audit_log = AdminAuditLog(
        admin_user_id=admin_user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        note=note,
    )
    db.add(audit_log)
    db.flush()
    return audit_log
