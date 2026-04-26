from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from .company import Company
    from .user import User


class CompanyRecruiter(Base):
    __tablename__ = "company_recruiters"
    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "recruiter_user_id",
            name="uq_company_recruiter_company_id_recruiter_user_id",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recruiter_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    company: Mapped["Company"] = relationship(back_populates="recruiter_memberships")
    recruiter: Mapped["User"] = relationship(back_populates="company_memberships")
