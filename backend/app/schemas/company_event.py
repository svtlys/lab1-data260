"""
request and response schemas for company-created events.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


EVENT_TYPES = {"Career Fair", "Workshop", "Info Session", "Networking", "Hackathon", "Panel"}
CITY_SET = {"Sunnyvale", "Cupertino", "Mountain View"}


class CompanyEventCreateRequest(BaseModel):
    """validate fields required to create a company event."""

    title: str = Field(min_length=2, max_length=200)
    description: str = Field(default="", max_length=5000)
    event_type: str = Field(min_length=2, max_length=100)
    city: str = Field(min_length=2, max_length=100)
    is_virtual: bool = False
    location: str = Field(default="", max_length=200)
    event_date: datetime
    capacity: int = Field(ge=1, le=10000)
    eligible_majors: str | None = Field(default=None, max_length=500)
    min_cgpa: float | None = Field(default=None, ge=0, le=4)
    min_grad_year: int | None = Field(default=None, ge=1900, le=2100)
    max_grad_year: int | None = Field(default=None, ge=1900, le=2100)

    @model_validator(mode="after")
    def validate_choices(self):
        """enforce pair 16 event choices on the server."""

        if self.event_type not in EVENT_TYPES:
            raise ValueError("event_type is not supported")
        if self.city not in CITY_SET:
            raise ValueError("city is not supported for pair 16")
        if not self.is_virtual and not self.location.strip():
            raise ValueError("location is required for in-person events")
        if self.max_grad_year is not None and self.min_grad_year is not None and self.max_grad_year < self.min_grad_year:
            raise ValueError("max_grad_year cannot be below min_grad_year")
        return self


class CompanyEventResponse(BaseModel):
    """return a company event and its registration count."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int | None = None
    title: str
    description: str
    organizer: str
    location: str
    city: str
    event_date: datetime
    event_type: str
    is_virtual: bool
    capacity: int
    eligible_majors: str | None = None
    min_cgpa: float | None = None
    min_grad_year: int | None = None
    max_grad_year: int | None = None
    eligibility_note: str | None = None
    registered_count: int = 0
    created_at: datetime
    updated_at: datetime


class EventRegistrationStudentResponse(BaseModel):
    """return a registered student's profile and eligibility result."""

    student_id: int
    student_name: str
    college_name: str
    major: str | None = None
    cgpa: float | None = None
    graduation_year: int | None = None
    registered_at: datetime
    eligible: bool
    ineligible_reasons: list[str]
