"""
request and response schemas for job workflows.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, model_validator


# keep job type values identical to the seed data and frontend filters
EmploymentType = Literal["Internship", "Full-time", "Part-time", "On-campus"]
EMPLOYMENT_TYPE_VALUES = get_args(EmploymentType)


class JobCreateRequest(BaseModel):
    """validate fields required to create a job posting."""

    title: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=10, max_length=10000)
    employment_type: EmploymentType
    city: str = Field(min_length=2, max_length=100)
    is_remote: bool = False
    salary_min: Decimal | None = Field(default=None, ge=0)
    salary_max: Decimal | None = Field(default=None, ge=0)
    required_skills: str | None = Field(default=None, max_length=5000)
    deadline: date | None = None

    @model_validator(mode="after")
    def validate_salary_range(self):
        """ensure the maximum salary is not below the minimum."""

        if (
            self.salary_min is not None
            and self.salary_max is not None
            and self.salary_max < self.salary_min
        ):
            raise ValueError("salary_max cannot be below salary_min")
        return self


class JobResponse(BaseModel):
    """return one job posting."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int | None = None
    title: str
    description: str
    company_name: str
    location: str
    city: str
    employment_type: EmploymentType
    is_remote: bool
    salary_min: Decimal | None = None
    salary_max: Decimal | None = None
    required_skills: str | None = None
    posted_at: datetime
    deadline: date | None = None
    applicant_count: int = 0
    pending_count: int = 0
