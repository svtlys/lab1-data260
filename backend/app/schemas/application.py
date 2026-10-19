"""
request and response schemas for job applications.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


ApplicationStatus = Literal["Pending", "Reviewed", "Declined"]


class ApplicationStatusUpdateRequest(BaseModel):
    """validate a company-side application status update."""

    status: ApplicationStatus


class ApplicationResponse(BaseModel):
    """return an application without exposing stored file paths."""

    id: int
    job_id: int
    student_id: int
    status: ApplicationStatus
    applied_at: datetime
    resume_filename: str | None = None
    job_title: str | None = None
    company_name: str | None = None
    student_name: str | None = None
    college_name: str | None = None
    major: str | None = None
