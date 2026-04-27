from sqlalchemy.orm import Session

from app.domains.companies.repository import (
    get_company_by_id,
    is_company_member,
)
from app.domains.jobs.repository import (
    create_job,
    get_approved_job_by_id,
    list_jobs,
    list_jobs_for_recruiter_scope,
)
from app.domains.jobs.schemas import JobCreateRequest, JobListQueryParams
from app.domains.jobs.tags import replace_job_tags
from app.models.job import Job, JobModerationStatus


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

    job = create_job(
        db,
        company_id=payload.company_id,
        title=payload.title,
        location=payload.location,
        employment_type=payload.employment_type,
        description=payload.description,
    )
    replace_job_tags(db, job_id=job.id, tag_slugs=payload.tags)
    db.refresh(job)
    return job


def list_public_jobs(db: Session, *, query: JobListQueryParams) -> list[Job]:
    return list_jobs(
        db,
        company_id=query.company_id,
        title_query=query.title_query,
        location=query.location,
        employment_type=query.employment_type,
        tag_slugs=query.tags,
        moderation_status=JobModerationStatus.APPROVED,
        page=query.page,
        page_size=query.page_size,
    )


def list_recruiter_jobs(
    db: Session, *, recruiter_user_id: int, query: JobListQueryParams
) -> list[Job]:
    return list_jobs_for_recruiter_scope(
        db,
        recruiter_user_id=recruiter_user_id,
        company_id=query.company_id,
        title_query=query.title_query,
        location=query.location,
        employment_type=query.employment_type,
        tag_slugs=query.tags,
        page=query.page,
        page_size=query.page_size,
    )


def get_public_job(db: Session, *, job_id: int) -> Job | None:
    return get_approved_job_by_id(db, job_id=job_id)
