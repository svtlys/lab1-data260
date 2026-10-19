"""
event registration model for students.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class EventRegistration(Base):
    """store one student's registration for one event."""

    __tablename__ = "event_registrations"
    __table_args__ = (
        # prevent one student from registering for the same event twice
        UniqueConstraint(
            "event_id",
            "student_id",
            name="uq_event_student",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id"),
        nullable=False,
    )
    student_id: Mapped[int] = mapped_column(
        ForeignKey("student_profiles.id"),
        nullable=False,
    )
    registered_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        nullable=False,
    )

    # connect a registration back to its event
    event: Mapped["Event"] = relationship(back_populates="registrations")

    # connect a registration back to its student profile
    student: Mapped["StudentProfile"] = relationship()
