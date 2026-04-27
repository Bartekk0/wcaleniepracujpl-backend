import logging

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.db.session import SessionLocal
from app.domains.notifications.transport import EmailDeliveryError, deliver_plain_email
from app.models.application import Application
from app.models.user import User
from app.worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="notifications.application_submitted",
    max_retries=3,
    default_retry_delay=60,
)
def notify_application_submitted(
    self,
    *,
    application_id: int,
    job_id: int,
    candidate_user_id: int,
) -> None:
    try:
        _notify_application_submitted_impl(
            application_id=application_id,
            job_id=job_id,
            candidate_user_id=candidate_user_id,
        )
    except EmailDeliveryError as exc:
        logger.exception(
            "Application submitted notification delivery failed",
            extra={"application_id": application_id},
        )
        raise self.retry(exc=exc) from exc


def _notify_application_submitted_impl(
    *,
    application_id: int,
    job_id: int,
    candidate_user_id: int,
) -> None:
    db = SessionLocal()
    try:
        stmt = (
            select(Application)
            .options(joinedload(Application.job), joinedload(Application.candidate))
            .where(Application.id == application_id)
        )
        application = db.execute(stmt).unique().scalar_one_or_none()
        if application is None:
            logger.warning("Application not found; skip notification", extra={"application_id": application_id})
            return
        if application.job_id != job_id or application.candidate_user_id != candidate_user_id:
            logger.warning(
                "Application id mismatch; skip notification",
                extra={
                    "application_id": application_id,
                    "expected_job": job_id,
                    "expected_candidate": candidate_user_id,
                },
            )
            return

        candidate = application.candidate
        job = application.job
        subject = f"Application received: {job.title}"
        body = (
            f'Your application for "{job.title}" (application id {application.id}) was submitted successfully.\n'
            f"Job id: {job.id}\n"
        )
        deliver_plain_email(
            to_addresses=[candidate.email],
            subject=subject,
            body=body,
        )
    finally:
        db.close()


@celery_app.task(
    bind=True,
    name="notifications.application_status_changed",
    max_retries=3,
    default_retry_delay=60,
)
def notify_application_status_changed(
    self,
    *,
    application_id: int,
    job_id: int,
    candidate_user_id: int,
    actor_user_id: int,
    from_status: str,
    to_status: str,
) -> None:
    try:
        _notify_application_status_changed_impl(
            application_id=application_id,
            job_id=job_id,
            candidate_user_id=candidate_user_id,
            actor_user_id=actor_user_id,
            from_status=from_status,
            to_status=to_status,
        )
    except EmailDeliveryError as exc:
        logger.exception(
            "Application status notification delivery failed",
            extra={"application_id": application_id},
        )
        raise self.retry(exc=exc) from exc


def _notify_application_status_changed_impl(
    *,
    application_id: int,
    job_id: int,
    candidate_user_id: int,
    actor_user_id: int,
    from_status: str,
    to_status: str,
) -> None:
    db = SessionLocal()
    try:
        stmt = (
            select(Application)
            .options(joinedload(Application.job), joinedload(Application.candidate))
            .where(Application.id == application_id)
        )
        application = db.execute(stmt).unique().scalar_one_or_none()
        if application is None:
            logger.warning("Application not found; skip notification", extra={"application_id": application_id})
            return
        if application.job_id != job_id or application.candidate_user_id != candidate_user_id:
            logger.warning("Application id mismatch; skip notification", extra={"application_id": application_id})
            return

        actor = db.get(User, actor_user_id)
        actor_label = actor.email if actor is not None else f"user id {actor_user_id}"
        candidate = application.candidate
        job = application.job
        subject = f"Application update: {job.title}"
        body = (
            f'Your application for "{job.title}" (id {application.id}) was updated from {from_status} to {to_status}.\n'
            f"Updated by: {actor_label}\n"
        )
        deliver_plain_email(
            to_addresses=[candidate.email],
            subject=subject,
            body=body,
        )
    finally:
        db.close()
