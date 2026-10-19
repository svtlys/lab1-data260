"""
job application model.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Application(Base):
    """store one student's application for one job."""

    __tablename__ = "applications"
    __table_args__ = (
        # prevent one student from applying to the same job twice
        UniqueConstraint(
            "job_id",
            "student_id",
            name="uq_app_job_student",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    student_id: Mapped[int] = mapped_column(
        ForeignKey("student_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="Pending",
        nullable=False,
    )
    applied_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        nullable=False,
    )
    resume_filename: Mapped[str | None] = mapped_column(String(255))
    resume_path: Mapped[str | None] = mapped_column(String(500))
