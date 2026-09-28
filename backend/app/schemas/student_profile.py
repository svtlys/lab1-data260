"""
request and response schemas for student profiles.
"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class StudentProfileResponse(BaseModel):
    """return a student's profile information."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    full_name: str
    college_name: str
    career_objective: str | None = None
    date_of_birth: date | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    degree: str | None = None
    major: str | None = None
    graduation_year: int | None = None
    cgpa: Decimal | None = Field(default=None, ge=0, le=10)
    experience: str | None = None
    skills: str | None = None
    phone: str | None = None
    profile_picture_url: str | None = None
    created_at: datetime
    updated_at: datetime


class StudentProfileUpdateRequest(BaseModel):
    """validate fields that a student may update."""

    full_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
    )
    college_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=200,
    )
    career_objective: str | None = None
    date_of_birth: date | None = None
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)
    degree: str | None = Field(default=None, max_length=150)
    major: str | None = Field(default=None, max_length=150)
    graduation_year: int | None = Field(
        default=None,
        ge=1900,
        le=2100,
    )
    cgpa: Decimal | None = Field(
        default=None,
        ge=0,
        le=10,
    )
    experience: str | None = None
    skills: str | None = None
    phone: str | None = Field(default=None, max_length=30)
    profile_picture_url: str | None = Field(
        default=None,
        max_length=500,
    )