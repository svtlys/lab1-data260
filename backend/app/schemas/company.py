"""
request and response schemas for company workflows.
"""

from pydantic import BaseModel, ConfigDict, Field


class CompanyProfileResponse(BaseModel):
    """return the logged-in company's profile."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    company_name: str
    location: str
    description: str | None = None
    contact_phone: str | None = None
    profile_picture_url: str | None = None


class CompanyProfileUpdateRequest(BaseModel):
    """validate fields a company may update."""

    company_name: str | None = Field(default=None, min_length=2, max_length=200)
    location: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    contact_phone: str | None = Field(default=None, max_length=30)
    profile_picture_url: str | None = Field(default=None, max_length=500)
