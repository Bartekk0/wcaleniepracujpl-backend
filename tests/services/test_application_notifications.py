from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db import models_registry  # noqa: F401
from app.db.base import Base
from app.domains.applications.schemas import ApplicationCreateRequest
from app.domains.applications.service import apply_to_job, change_application_status
from app.models.application import ApplicationStatus
from app.models.company import Company
from app.models.job import Job
from app.models.user import UserRole
from app.services.user_service import create_user


def _build_test_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return session_factory()


def test_apply_to_job_enqueues_submitted_notification(monkeypatch) -> None:
    db = _build_test_session()
    try:
        recruiter = create_user(
            db=db,
            email="notify.recruiter@example.com",
            password="StrongPass123!",
            role=UserRole.RECRUITER,
        )
        candidate = create_user(
            db=db,
            email="notify.candidate@example.com",
            password="StrongPass123!",
            role=UserRole.CANDIDATE,
        )
        company = Company(owner_user_id=recruiter.id, name="Notify Co")
        db.add(company)
        db.commit()
        db.refresh(company)
        job = Job(company_id=company.id, title="Backend", description="Build APIs")
        db.add(job)
        db.commit()
        db.refresh(job)

        captured: dict[str, int] = {}

        def _capture_submission(**kwargs) -> None:
            captured.update(kwargs)

        monkeypatch.setattr(
            "app.domains.applications.service.enqueue_application_submitted_notification",
            _capture_submission,
        )

        application = apply_to_job(
            db,
            candidate_user_id=candidate.id,
            payload=ApplicationCreateRequest(job_id=job.id, cover_letter="Interested"),
        )

        assert captured["application_id"] == application.id
        assert captured["job_id"] == job.id
        assert captured["candidate_user_id"] == candidate.id
    finally:
        db.close()


def test_change_application_status_enqueues_status_change_notification(monkeypatch) -> None:
    db = _build_test_session()
    try:
        recruiter = create_user(
            db=db,
            email="notify.status.recruiter@example.com",
            password="StrongPass123!",
            role=UserRole.RECRUITER,
        )
        candidate = create_user(
            db=db,
            email="notify.status.candidate@example.com",
            password="StrongPass123!",
            role=UserRole.CANDIDATE,
        )
        company = Company(owner_user_id=recruiter.id, name="Status Notify Co")
        db.add(company)
        db.commit()
        db.refresh(company)
        job = Job(company_id=company.id, title="Data Engineer", description="Build pipelines")
        db.add(job)
        db.commit()
        db.refresh(job)

        application = apply_to_job(
            db,
            candidate_user_id=candidate.id,
            payload=ApplicationCreateRequest(job_id=job.id, cover_letter=None),
        )

        captured: dict[str, object] = {}

        def _capture_status_change(**kwargs) -> None:
            captured.update(kwargs)

        monkeypatch.setattr(
            "app.domains.applications.service.enqueue_application_status_changed_notification",
            _capture_status_change,
        )

        updated = change_application_status(
            db,
            actor_user_id=recruiter.id,
            actor_role=UserRole.RECRUITER,
            application_id=application.id,
            new_status=ApplicationStatus.REVIEWING,
        )

        assert updated.status == ApplicationStatus.REVIEWING
        assert captured["application_id"] == application.id
        assert captured["job_id"] == job.id
        assert captured["candidate_user_id"] == candidate.id
        assert captured["actor_user_id"] == recruiter.id
        assert captured["from_status"] == ApplicationStatus.SUBMITTED
        assert captured["to_status"] == ApplicationStatus.REVIEWING
    finally:
        db.close()
