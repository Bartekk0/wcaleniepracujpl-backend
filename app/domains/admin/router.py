from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.domains.admin.schemas import (
    AdminAuditLogOut,
    ModerationActionResponse,
    ModerationDecisionRequest,
    ModerationJobOut,
)
from app.domains.admin.service import approve_job, get_moderation_queue, reject_job
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
    except ValueError as exc:
        message = str(exc)
        if message == "Job not found.":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc

    return ModerationActionResponse(
        job=ModerationJobOut.model_validate(job),
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
    except ValueError as exc:
        message = str(exc)
        if message == "Job not found.":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc

    return ModerationActionResponse(
        job=ModerationJobOut.model_validate(job),
        audit_log=AdminAuditLogOut.model_validate(audit_log),
    )
