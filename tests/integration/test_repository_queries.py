from sqlalchemy.orm import Session

from app.domains.applications.repository import (
    list_applications_for_candidate,
    list_applications_for_candidate_by_status,
    list_applications_for_job,
    list_applications_for_job_by_status,
)
from app.domains.companies.repository import add_recruiter_to_company
from app.domains.jobs.repository import list_jobs_for_recruiter_scope
from app.models.application import Application, ApplicationStatus
from app.models.company import Company
from app.models.job import Job
from app.models.user import User, UserRole


def _create_user(
    db_session: Session,
    *,
    email: str,
    role: UserRole,
) -> User:
    user = User(
        email=email,
        hashed_password="hashed",
        role=role,
        is_activated=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_list_jobs_for_recruiter_scope_includes_owned_and_membership_jobs(
    db_session: Session,
) -> None:
    owner = _create_user(
        db_session,
        email="repo.owner@example.com",
        role=UserRole.RECRUITER,
    )
    member = _create_user(
        db_session,
        email="repo.member@example.com",
        role=UserRole.RECRUITER,
    )
    outsider = _create_user(
        db_session,
        email="repo.outsider@example.com",
        role=UserRole.RECRUITER,
    )

    company_owned = Company(owner_user_id=owner.id, name="Owned Co")
    company_other = Company(owner_user_id=outsider.id, name="Other Co")
    db_session.add_all([company_owned, company_other])
    db_session.commit()
    db_session.refresh(company_owned)
    db_session.refresh(company_other)

    add_recruiter_to_company(
        db_session,
        company_id=company_other.id,
        recruiter_user_id=member.id,
    )

    owned_job = Job(
        company_id=company_owned.id,
        title="Owned Job",
        description="Owned by recruiter",
    )
    membership_job = Job(
        company_id=company_other.id,
        title="Membership Job",
        description="Visible through membership",
    )
    db_session.add_all([owned_job, membership_job])
    db_session.commit()

    owner_scope = list_jobs_for_recruiter_scope(db_session, recruiter_user_id=owner.id)
    member_scope = list_jobs_for_recruiter_scope(db_session, recruiter_user_id=member.id)
    outsider_scope = list_jobs_for_recruiter_scope(db_session, recruiter_user_id=outsider.id)

    assert [job.title for job in owner_scope] == ["Owned Job"]
    assert [job.title for job in member_scope] == ["Membership Job"]
    assert [job.title for job in outsider_scope] == ["Membership Job"]


def test_application_repository_candidate_and_status_filtered_queries(db_session: Session) -> None:
    recruiter = _create_user(
        db_session,
        email="repo.query.recruiter@example.com",
        role=UserRole.RECRUITER,
    )
    candidate = _create_user(
        db_session,
        email="repo.query.candidate@example.com",
        role=UserRole.CANDIDATE,
    )
    company = Company(owner_user_id=recruiter.id, name="Repo Query Co")
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)

    job = Job(
        company_id=company.id,
        title="Repo Query Job",
        description="Query behavior verification",
    )
    job_second = Job(
        company_id=company.id,
        title="Repo Query Job 2",
        description="Second job for candidate listing",
    )
    db_session.add_all([job, job_second])
    db_session.commit()
    db_session.refresh(job)
    db_session.refresh(job_second)

    submitted = Application(
        job_id=job.id,
        candidate_user_id=candidate.id,
        cover_letter="Submitted",
        status=ApplicationStatus.SUBMITTED,
    )
    reviewing = Application(
        job_id=job_second.id,
        candidate_user_id=candidate.id,
        cover_letter="Reviewing",
        status=ApplicationStatus.REVIEWING,
    )
    db_session.add_all([submitted, reviewing])
    db_session.commit()

    by_candidate = list_applications_for_candidate(db_session, candidate_user_id=candidate.id)
    by_candidate_submitted = list_applications_for_candidate_by_status(
        db_session,
        candidate_user_id=candidate.id,
        status=ApplicationStatus.SUBMITTED,
    )
    by_job = list_applications_for_job(db_session, job_id=job.id)
    by_job_reviewing = list_applications_for_job_by_status(
        db_session,
        job_id=job_second.id,
        status=ApplicationStatus.REVIEWING,
    )

    assert len(by_candidate) == 2
    assert [app.status for app in by_candidate_submitted] == [ApplicationStatus.SUBMITTED]
    assert len(by_job) == 1
    assert [app.status for app in by_job_reviewing] == [ApplicationStatus.REVIEWING]
