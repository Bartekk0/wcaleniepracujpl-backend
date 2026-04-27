from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.db.session import get_db
from app.domains.admin.exceptions import (
    AlreadyModeratedError,
    JobNotFoundError,
    ReportAlreadyHandledError,
    ReportNotFoundError,
)
from app.domains.admin.schemas import (
    AdminAuditLogOut,
    CreateReportRequest,
    ModerationActionResponse,
    ModerationDecisionRequest,
    ModerationJobOut,
    ReportActionResponse,
    ReportDecisionRequest,
    ReportOut,
)
from app.domains.admin.service import (
    approve_job,
    dismiss_report,
    get_moderation_queue,
    get_reports_queue,
    reject_job,
    resolve_report,
    submit_report,
)
from app.models.report import ReportStatus
from app.models.user import User

router = APIRouter()


@router.get(
    "/moderation/jobs",
    response_model=list[ModerationJobOut],
    dependencies=[Depends(require_admin)],
)
def list_moderation_jobs_endpoint(
    db: Session = Depends(get_db),
) -> list[ModerationJobOut]:
    jobs = get_moderation_queue(db)
    return [ModerationJobOut.model_validate(job) for job in jobs]


@router.post("/moderation/jobs/{job_id}/approve", response_model=ModerationActionResponse)
def approve_job_endpoint(
    job_id: int,
    payload: ModerationDecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> ModerationActionResponse:
    try:
        job, audit_log = approve_job(
            db,
            admin_user_id=current_user.id,
            job_id=job_id,
            note=payload.note,
        )
    except JobNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AlreadyModeratedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return ModerationActionResponse(
        job=ModerationJobOut.model_validate(job),
        audit_log=AdminAuditLogOut.model_validate(audit_log),
    )


@router.post(
    "/reports/jobs/{job_id}", response_model=ReportOut, status_code=status.HTTP_201_CREATED
)
def create_report_endpoint(
    job_id: int,
    payload: CreateReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportOut:
    try:
        report = submit_report(
            db,
            reporter_user_id=current_user.id,
            job_id=job_id,
            reason=payload.reason,
        )
    except JobNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ReportOut.model_validate(report)


@router.get(
    "/reports",
    response_model=list[ReportOut],
    dependencies=[Depends(require_admin)],
)
def list_reports_endpoint(
    status_filter: ReportStatus | None = None,
    db: Session = Depends(get_db),
) -> list[ReportOut]:
    reports = get_reports_queue(db, status=status_filter)
    return [ReportOut.model_validate(report) for report in reports]


@router.post("/reports/{report_id}/resolve", response_model=ReportActionResponse)
def resolve_report_endpoint(
    report_id: int,
    payload: ReportDecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> ReportActionResponse:
    try:
        report, audit_log = resolve_report(
            db,
            admin_user_id=current_user.id,
            report_id=report_id,
            note=payload.note,
        )
    except ReportNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ReportAlreadyHandledError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return ReportActionResponse(
        report=ReportOut.model_validate(report),
        audit_log=AdminAuditLogOut.model_validate(audit_log),
    )


@router.post("/reports/{report_id}/dismiss", response_model=ReportActionResponse)
def dismiss_report_endpoint(
    report_id: int,
    payload: ReportDecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> ReportActionResponse:
    try:
        report, audit_log = dismiss_report(
            db,
            admin_user_id=current_user.id,
            report_id=report_id,
            note=payload.note,
        )
    except ReportNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ReportAlreadyHandledError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return ReportActionResponse(
        report=ReportOut.model_validate(report),
        audit_log=AdminAuditLogOut.model_validate(audit_log),
    )


@router.post("/moderation/jobs/{job_id}/reject", response_model=ModerationActionResponse)
def reject_job_endpoint(
    job_id: int,
    payload: ModerationDecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> ModerationActionResponse:
    try:
        job, audit_log = reject_job(
            db,
            admin_user_id=current_user.id,
            job_id=job_id,
            note=payload.note,
        )
    except JobNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AlreadyModeratedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return ModerationActionResponse(
        job=ModerationJobOut.model_validate(job),
        audit_log=AdminAuditLogOut.model_validate(audit_log),
    )
