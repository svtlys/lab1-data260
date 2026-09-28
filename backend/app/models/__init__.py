"""
make all database models available from one package.
"""

from app.models.company_profile import CompanyProfile
from app.models.student_profile import StudentProfile
from app.models.user import User, UserRole

__all__ = [
    "CompanyProfile",
    "StudentProfile",
    "User",
    "UserRole",
]