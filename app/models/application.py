from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from .application_event import ApplicationEvent
    from .job import Job
    from .user import User


class ApplicationStatus(StrEnum):
    SUBMITTED = "submitted"
    REVIEWING = "reviewing"
    REJECTED = "rejected"
    ACCEPTED = "accepted"


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("job_id", "candidate_user_id", name="uq_applications_job_candidate"),
        Index("ix_applications_job_status", "job_id", "status"),
        Index("ix_applications_candidate_status", "candidate_user_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    candidate_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cover_letter: Mapped[str | None] = mapped_column(Text, nullable=True)
    cv_object_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, name="application_status"),
        default=ApplicationStatus.SUBMITTED,
        server_default=text("'SUBMITTED'"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    job: Mapped["Job"] = relationship(back_populates="applications")
    candidate: Mapped["User"] = relationship(back_populates="applications")
    events: Mapped[list["ApplicationEvent"]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="ApplicationEvent.id.asc()",
    )
