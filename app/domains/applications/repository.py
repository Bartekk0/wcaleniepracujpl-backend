from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application import Application, ApplicationStatus


def create_application(
    db: Session,
    *,
    job_id: int,
    candidate_user_id: int,
    cover_letter: str | None,
) -> Application:
    application = Application(
        job_id=job_id,
        candidate_user_id=candidate_user_id,
        cover_letter=cover_letter,
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


def get_application_by_job_and_candidate(
    db: Session,
    *,
    job_id: int,
    candidate_user_id: int,
) -> Application | None:
    stmt = select(Application).where(
        Application.job_id == job_id,
        Application.candidate_user_id == candidate_user_id,
    )
    return db.execute(stmt).scalar_one_or_none()


def list_applications_for_candidate(db: Session, *, candidate_user_id: int) -> list[Application]:
    stmt = (
        select(Application)
        .where(Application.candidate_user_id == candidate_user_id)
        .order_by(Application.id.desc())
    )
    return list(db.execute(stmt).scalars().all())


def list_applications_for_job(db: Session, *, job_id: int) -> list[Application]:
    stmt = select(Application).where(Application.job_id == job_id).order_by(Application.id.desc())
    return list(db.execute(stmt).scalars().all())


def list_applications_for_candidate_by_status(
    db: Session,
    *,
    candidate_user_id: int,
    status: ApplicationStatus,
) -> list[Application]:
    stmt = (
        select(Application)
        .where(
            Application.candidate_user_id == candidate_user_id,
            Application.status == status,
        )
        .order_by(Application.id.desc())
    )
    return list(db.execute(stmt).scalars().all())


def list_applications_for_job_by_status(
    db: Session,
    *,
    job_id: int,
    status: ApplicationStatus,
) -> list[Application]:
    stmt = (
        select(Application)
        .where(
            Application.job_id == job_id,
            Application.status == status,
        )
        .order_by(Application.id.desc())
    )
    return list(db.execute(stmt).scalars().all())


def get_application_by_id(db: Session, *, application_id: int) -> Application | None:
    stmt = select(Application).where(Application.id == application_id)
    return db.execute(stmt).scalar_one_or_none()


def update_application_status(
    db: Session,
    *,
    application: Application,
    status: ApplicationStatus,
) -> Application:
    application.status = status
    db.add(application)
    db.commit()
    db.refresh(application)
    return application
