import logging

from app.worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="notifications.application_submitted")
def notify_application_submitted(
    *,
    application_id: int,
    job_id: int,
    candidate_user_id: int,
) -> None:
    # Transport is intentionally simple for now (log-only stub).
    logger.info(
        "Notification stub: application submitted",
        extra={
            "application_id": application_id,
            "job_id": job_id,
            "candidate_user_id": candidate_user_id,
        },
    )


@celery_app.task(name="notifications.application_status_changed")
def notify_application_status_changed(
    *,
    application_id: int,
    job_id: int,
    candidate_user_id: int,
    actor_user_id: int,
    from_status: str,
    to_status: str,
) -> None:
    # Transport is intentionally simple for now (log-only stub).
    logger.info(
        "Notification stub: application status changed",
        extra={
            "application_id": application_id,
            "job_id": job_id,
            "candidate_user_id": candidate_user_id,
            "actor_user_id": actor_user_id,
            "from_status": from_status,
            "to_status": to_status,
        },
    )
