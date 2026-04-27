from sqlalchemy import or_, select
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


def list_jobs(db: Session) -> list[Job]:
    stmt = select(Job).order_by(Job.id.desc())
    return list(db.execute(stmt).scalars().all())


def get_job_by_id(db: Session, *, job_id: int) -> Job | None:
    stmt = select(Job).where(Job.id == job_id)
    return db.execute(stmt).scalar_one_or_none()


def list_jobs_for_recruiter_scope(db: Session, *, recruiter_user_id: int) -> list[Job]:
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
        .order_by(Job.id.desc())
        .distinct()
    )
    return list(db.execute(stmt).scalars().all())
