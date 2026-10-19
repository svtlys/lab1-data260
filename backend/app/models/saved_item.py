"""
saved item model for student jobs and events.
"""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SavedItem(Base):
    """store one saved job or event for one student."""

    __tablename__ = "saved_items"
    __table_args__ = (
        # prevent saving the same job more than once for one student
        UniqueConstraint(
            "student_id",
            "job_id",
            name="uq_saved_student_job",
        ),
        # prevent saving the same event more than once for one student
        UniqueConstraint(
            "student_id",
            "event_id",
            name="uq_saved_student_event",
        ),
        # require every saved item to point to exactly one item type
        CheckConstraint(
            "(job_id IS NOT NULL AND event_id IS NULL) OR "
            "(job_id IS NULL AND event_id IS NOT NULL)",
            name="chk_saved_item_type",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("student_profiles.id"),
        nullable=False,
    )
    job_id: Mapped[int | None] = mapped_column(ForeignKey("jobs.id"))
    event_id: Mapped[int | None] = mapped_column(ForeignKey("events.id"))
    saved_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        nullable=False,
    )
