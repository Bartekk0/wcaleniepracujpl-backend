from sqlalchemy import select
from sqlalchemy.orm import Session

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

