from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.company_recruiter import CompanyRecruiter
from app.models.job import Job


def create_job(
    db: Session,
    *,
    company_id: int,
    title: str,
    location: str | None,
    employment_type: str | None,
    description: str,
) -> Job:
    job = Job(
        company_id=company_id,
        title=title,
        location=location,
        employment_type=employment_type,
        description=description,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _apply_job_filters(
    stmt: Select[tuple[Job]],
    *,
    company_id: int | None,
    title_query: str | None,
    location: str | None,
    employment_type: str | None,
) -> Select[tuple[Job]]:
    if company_id is not None:
        stmt = stmt.where(Job.company_id == company_id)
    if title_query:
        stmt = stmt.where(Job.title.ilike(f"%{title_query}%"))
    if location:
        stmt = stmt.where(Job.location.ilike(f"%{location}%"))
    if employment_type:
        stmt = stmt.where(Job.employment_type == employment_type)
    return stmt


def list_jobs(
    db: Session,
    *,
    company_id: int | None = None,
    title_query: str | None = None,
    location: str | None = None,
    employment_type: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> list[Job]:
    stmt = select(Job)
    stmt = _apply_job_filters(
        stmt,
        company_id=company_id,
        title_query=title_query,
        location=location,
        employment_type=employment_type,
    )
    stmt = stmt.order_by(Job.id.desc()).offset((page - 1) * page_size).limit(page_size)
    return list(db.execute(stmt).scalars().all())


def get_job_by_id(db: Session, *, job_id: int) -> Job | None:
    stmt = select(Job).where(Job.id == job_id)
    return db.execute(stmt).scalar_one_or_none()


def list_jobs_for_recruiter_scope(
    db: Session,
    *,
    recruiter_user_id: int,
    company_id: int | None = None,
    title_query: str | None = None,
    location: str | None = None,
    employment_type: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> list[Job]:
    stmt = (
        select(Job)
        .join(Company, Company.id == Job.company_id)
        .outerjoin(
            CompanyRecruiter,
            CompanyRecruiter.company_id == Company.id,
        )
        .where(
            or_(
                Company.owner_user_id == recruiter_user_id,
                CompanyRecruiter.recruiter_user_id == recruiter_user_id,
            )
        )
    )
    stmt = _apply_job_filters(
        stmt,
        company_id=company_id,
        title_query=title_query,
        location=location,
        employment_type=employment_type,
    )
    stmt = stmt.order_by(Job.id.desc()).distinct().offset((page - 1) * page_size).limit(page_size)
    return list(db.execute(stmt).scalars().all())
