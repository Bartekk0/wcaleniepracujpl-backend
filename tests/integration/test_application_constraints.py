from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.company import Company
from app.models.job import Job
from app.models.user import User, UserRole


def test_applications_unique_constraint_on_job_and_candidate(db_session: Session) -> None:
    recruiter = User(
        email="integration.recruiter@example.com",
        hashed_password="hashed",
        role=UserRole.RECRUITER,
        is_activated=True,
    )
    candidate = User(
        email="integration.candidate@example.com",
        hashed_password="hashed",
        role=UserRole.CANDIDATE,
        is_activated=True,
    )
    db_session.add_all([recruiter, candidate])
    db_session.commit()
    db_session.refresh(recruiter)
    db_session.refresh(candidate)

    company = Company(owner_user_id=recruiter.id, name="Integration Co")
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)

    job = Job(
        company_id=company.id,
        title="Integration Backend Engineer",
        description="Integration test job",
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    first = Application(
        job_id=job.id,
        candidate_user_id=candidate.id,
        cover_letter="First application",
    )
    db_session.add(first)
    db_session.commit()

    duplicate = Application(
        job_id=job.id,
        candidate_user_id=candidate.id,
        cover_letter="Duplicate application",
    )
    db_session.add(duplicate)

    try:
        db_session.commit()
        raise AssertionError("Expected unique constraint violation on duplicate application.")
    except IntegrityError:
        db_session.rollback()
