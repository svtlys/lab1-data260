"""
event model for student discovery and registration.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Event(Base):
    """store an event that students can search and view."""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("company_profiles.id", ondelete="CASCADE"),
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    organizer: Mapped[str] = mapped_column(String(200), nullable=False)
    location: Mapped[str] = mapped_column(String(200), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    event_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    is_virtual: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    capacity: Mapped[int | None] = mapped_column(Integer)
    eligible_majors: Mapped[str | None] = mapped_column(String(500))
    min_cgpa: Mapped[float | None] = mapped_column(Numeric(3, 2))
    min_grad_year: Mapped[int | None] = mapped_column(Integer)
    max_grad_year: Mapped[int | None] = mapped_column(Integer)
    eligibility_note: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    # connect each event to its student registrations
    registrations: Mapped[list["EventRegistration"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
    )
