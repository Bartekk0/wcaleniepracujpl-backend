from app.domains.applications.constants import ALLOWED_STATUS_TRANSITIONS
from sqlalchemy.orm import Session

from app.domains.applications.repository import (
    create_application,
    get_application_by_id,
    get_application_by_job_and_candidate,
    list_applications_for_candidate,
    list_applications_for_job,
    update_application_status,
)
from app.domains.notifications.service import (
    enqueue_application_status_changed_notification,
    enqueue_application_submitted_notification,
)
from app.domains.companies.repository import is_company_member
from app.domains.jobs.repository import get_job_by_id
from app.domains.applications.schemas import ApplicationCreateRequest
from app.models.application import Application, ApplicationStatus
from app.models.user import UserRole


def apply_to_job(
    db: Session,
    *,
    candidate_user_id: int,
    payload: ApplicationCreateRequest,
) -> Application:
    job = get_job_by_id(db, job_id=payload.job_id)
    if job is None:
        raise ValueError("Job not found.")

    existing = get_application_by_job_and_candidate(
        db,
        job_id=payload.job_id,
        candidate_user_id=candidate_user_id,
    )
    if existing is not None:
        raise ValueError("Application already exists for this job.")

    application = create_application(
        db,
        job_id=payload.job_id,
        candidate_user_id=candidate_user_id,
        cover_letter=payload.cover_letter,
    )
    enqueue_application_submitted_notification(
        application_id=application.id,
        job_id=application.job_id,
        candidate_user_id=application.candidate_user_id,
    )
    return application


def list_my_applications(db: Session, *, candidate_user_id: int) -> list[Application]:
    return list_applications_for_candidate(db, candidate_user_id=candidate_user_id)


def _assert_recruiter_can_access_job(
    db: Session,
    *,
    job_id: int,
    recruiter_user_id: int,
) -> None:
    job = get_job_by_id(db, job_id=job_id)
    if job is None:
        raise ValueError("Job not found.")
    has_access = job.company.owner_user_id == recruiter_user_id or is_company_member(
        db,
        company_id=job.company_id,
        recruiter_user_id=recruiter_user_id,
    )
    if not has_access:
        raise PermissionError("Recruiter has no access to this job.")


def list_recruiter_applications_for_job(
    db: Session,
    *,
    recruiter_user_id: int,
    job_id: int,
) -> list[Application]:
    _assert_recruiter_can_access_job(db, job_id=job_id, recruiter_user_id=recruiter_user_id)
    return list_applications_for_job(db, job_id=job_id)


def change_application_status(
    db: Session,
    *,
    actor_user_id: int,
    actor_role: UserRole,
    application_id: int,
    new_status: ApplicationStatus,
) -> Application:
    if actor_role not in (UserRole.ADMIN, UserRole.RECRUITER):
        raise PermissionError("Only admins and recruiters can change application status.")

    application = get_application_by_id(db, application_id=application_id)
    if application is None:
        raise ValueError("Application not found.")

    if actor_role == UserRole.RECRUITER:
        _assert_recruiter_can_access_job(
            db,
            job_id=application.job_id,
            recruiter_user_id=actor_user_id,
        )

    allowed_targets = ALLOWED_STATUS_TRANSITIONS[application.status]
    if new_status not in allowed_targets:
        raise ValueError(
            f"Invalid status transition: {application.status.value} -> {new_status.value}."
        )

    previous_status = application.status
    updated = update_application_status(
        db,
        application=application,
        status=new_status,
    )
    enqueue_application_status_changed_notification(
        application_id=updated.id,
        job_id=updated.job_id,
        candidate_user_id=updated.candidate_user_id,
        actor_user_id=actor_user_id,
        from_status=previous_status,
        to_status=new_status,
    )
    return updated
