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

    return create_application(
        db,
        job_id=payload.job_id,
        candidate_user_id=candidate_user_id,
        cover_letter=payload.cover_letter,
    )


def list_my_applications(db: Session, *, candidate_user_id: int) -> list[Application]:
    return list_applications_for_candidate(db, candidate_user_id=candidate_user_id)


def list_recruiter_applications_for_job(
    db: Session,
    *,
    recruiter_user_id: int,
    job_id: int,
) -> list[Application]:
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
        job = get_job_by_id(db, job_id=application.job_id)
        if job is None:
            raise ValueError("Job not found.")
        has_access = job.company.owner_user_id == actor_user_id or is_company_member(
            db,
            company_id=job.company_id,
            recruiter_user_id=actor_user_id,
        )
        if not has_access:
            raise PermissionError("Recruiter has no access to this application.")

    allowed_targets = ALLOWED_STATUS_TRANSITIONS[application.status]
    if new_status not in allowed_targets:
        raise ValueError(
            f"Invalid status transition: {application.status.value} -> {new_status.value}."
        )

    return update_application_status(
        db,
        application=application,
        status=new_status,
    )
