from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from .job import Job


job_tag_map = Table(
    "job_tag_map",
    Base.metadata,
    Column("job_id", Integer, ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("job_tags.id", ondelete="CASCADE"), primary_key=True),
)


class JobTag(Base):
    __tablename__ = "job_tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    label: Mapped[str] = mapped_column(String(120), nullable=False)

    jobs: Mapped[list["Job"]] = relationship(
        secondary=job_tag_map,
        back_populates="tags",
        lazy="selectin",
    )
