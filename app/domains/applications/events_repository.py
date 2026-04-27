from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application import Application, ApplicationStatus
from app.models.application_event import ApplicationEvent


def create_application_event(
    db: Session,
    *,
    application: Application,
    actor_user_id: int,
    from_status: ApplicationStatus,
    to_status: ApplicationStatus,
    note: str | None = None,
) -> ApplicationEvent:
    event = ApplicationEvent(
        application_id=application.id,
        actor_user_id=actor_user_id,
        from_status=from_status,
        to_status=to_status,
        note=note,
    )
    db.add(event)
    db.flush()
    return event


def list_application_events(
    db: Session,
    *,
    application_id: int,
) -> list[ApplicationEvent]:
    stmt = (
        select(ApplicationEvent)
        .where(ApplicationEvent.application_id == application_id)
        .order_by(ApplicationEvent.id.asc())
    )
    return list(db.execute(stmt).scalars().all())
