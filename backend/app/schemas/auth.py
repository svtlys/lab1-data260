"""
request and response schemas for authentication.
"""

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class StudentSignupRequest(BaseModel):
    """validate data required to create a student account."""

    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    college_name: str = Field(min_length=2, max_length=200)


class CompanySignupRequest(BaseModel):
    """validate data required to create a company account."""

    company_name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    location: str = Field(min_length=2, max_length=200)


class LoginRequest(BaseModel):
    """validate data required for login."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    """return safe user information without the password hash."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    email: EmailStr
    is_active: bool


class TokenResponse(BaseModel):
    """return the JWT access token after successful login."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse