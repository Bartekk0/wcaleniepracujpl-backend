from sqlalchemy.orm import Session

from app.domains.companies.repository import (
    get_company_by_id,
    is_company_member,
)
from app.domains.jobs.repository import create_job, get_job_by_id, list_jobs
from app.domains.jobs.schemas import JobCreateRequest
from app.models.job import Job


def create_recruiter_job(
    db: Session,
    *,
    recruiter_user_id: int,
    payload: JobCreateRequest,
) -> Job:
    company = get_company_by_id(db, company_id=payload.company_id)
    if company is None:
        raise ValueError("Company not found.")

    has_access = company.owner_user_id == recruiter_user_id or is_company_member(
        db,
        company_id=company.id,
        recruiter_user_id=recruiter_user_id,
    )
    if not has_access:
        raise PermissionError("Recruiter has no access to this company.")

    return create_job(
        db,
        company_id=payload.company_id,
        title=payload.title,
        location=payload.location,
        employment_type=payload.employment_type,
        description=payload.description,
    )


def list_public_jobs(db: Session) -> list[Job]:
    return list_jobs(db)


def get_public_job(db: Session, *, job_id: int) -> Job | None:
    return get_job_by_id(db, job_id=job_id)

