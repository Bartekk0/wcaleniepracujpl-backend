from sqlalchemy.orm import Session

from app.domains.admin.constants import (
    JOB_APPROVED_AUDIT_ACTION,
    JOB_AUDIT_TARGET_TYPE,
    JOB_REJECTED_AUDIT_ACTION,
    REPORT_AUDIT_TARGET_TYPE,
    REPORT_DISMISSED_AUDIT_ACTION,
    REPORT_RESOLVED_AUDIT_ACTION,
)
from app.domains.admin.exceptions import (
    AlreadyModeratedError,
    JobNotFoundError,
    ReportAlreadyHandledError,
    ReportNotFoundError,
)
from app.domains.admin.repository import (
    create_admin_audit_log,
    create_report,
    get_report_for_update,
    list_reports,
    get_job_for_moderation,
    list_pending_moderation_jobs,
    set_report_resolution,
    set_job_moderation_result,
)
from app.domains.jobs.repository import get_job_by_id
from app.models.admin_audit_log import AdminAuditLog
from app.models.job import Job, JobModerationStatus
from app.models.report import Report, ReportStatus


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


def submit_report(
    db: Session,
    *,
    reporter_user_id: int,
    job_id: int,
    reason: str,
) -> Report:
    if get_job_by_id(db, job_id=job_id) is None:
        raise JobNotFoundError("Job not found.")
    return create_report(
        db,
        job_id=job_id,
        reporter_user_id=reporter_user_id,
        reason=reason,
    )


def get_reports_queue(
    db: Session,
    *,
    status: ReportStatus | None = None,
) -> list[Report]:
    return list_reports(db, status=status)


def resolve_report(
    db: Session,
    *,
    admin_user_id: int,
    report_id: int,
    note: str | None,
) -> tuple[Report, AdminAuditLog]:
    return _handle_report(
        db,
        admin_user_id=admin_user_id,
        report_id=report_id,
        note=note,
        status=ReportStatus.RESOLVED,
        action=REPORT_RESOLVED_AUDIT_ACTION,
    )


def dismiss_report(
    db: Session,
    *,
    admin_user_id: int,
    report_id: int,
    note: str | None,
) -> tuple[Report, AdminAuditLog]:
    return _handle_report(
        db,
        admin_user_id=admin_user_id,
        report_id=report_id,
        note=note,
        status=ReportStatus.DISMISSED,
        action=REPORT_DISMISSED_AUDIT_ACTION,
    )


def _handle_report(
    db: Session,
    *,
    admin_user_id: int,
    report_id: int,
    note: str | None,
    status: ReportStatus,
    action: str,
) -> tuple[Report, AdminAuditLog]:
    report = get_report_for_update(db, report_id=report_id)
    if report is None:
        raise ReportNotFoundError("Report not found.")
    if report.status != ReportStatus.OPEN:
        raise ReportAlreadyHandledError("Report is already handled.")

    set_report_resolution(
        db,
        report=report,
        status=status,
        admin_user_id=admin_user_id,
        note=note,
    )
    audit_log = create_admin_audit_log(
        db,
        admin_user_id=admin_user_id,
        action=action,
        target_type=REPORT_AUDIT_TARGET_TYPE,
        target_id=report.id,
        note=note,
    )
    db.commit()
    db.refresh(report)
    db.refresh(audit_log)
    return report, audit_log


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
        raise JobNotFoundError("Job not found.")
    if job.moderation_status != JobModerationStatus.PENDING:
        raise AlreadyModeratedError("Job is already moderated.")

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
