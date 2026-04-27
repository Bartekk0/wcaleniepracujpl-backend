import logging

from app.models.application import ApplicationStatus

logger = logging.getLogger(__name__)


def enqueue_application_submitted_notification(
    *,
    application_id: int,
    job_id: int,
    candidate_user_id: int,
) -> None:
    try:
        from app.domains.notifications.tasks import notify_application_submitted

        notify_application_submitted.delay(
            application_id=application_id,
            job_id=job_id,
            candidate_user_id=candidate_user_id,
        )
    except Exception:
        logger.exception(
            "Failed to enqueue application submitted notification task",
            extra={
                "application_id": application_id,
                "job_id": job_id,
                "candidate_user_id": candidate_user_id,
            },
        )


def enqueue_application_status_changed_notification(
    *,
    application_id: int,
    job_id: int,
    candidate_user_id: int,
    actor_user_id: int,
    from_status: ApplicationStatus,
    to_status: ApplicationStatus,
) -> None:
    try:
        from app.domains.notifications.tasks import notify_application_status_changed

        notify_application_status_changed.delay(
            application_id=application_id,
            job_id=job_id,
            candidate_user_id=candidate_user_id,
            actor_user_id=actor_user_id,
            from_status=from_status.value,
            to_status=to_status.value,
        )
    except Exception:
        logger.exception(
            "Failed to enqueue application status changed notification task",
            extra={
                "application_id": application_id,
                "job_id": job_id,
                "candidate_user_id": candidate_user_id,
                "actor_user_id": actor_user_id,
                "from_status": from_status.value,
                "to_status": to_status.value,
            },
        )
