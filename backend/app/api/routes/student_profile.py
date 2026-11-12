"""
protected student profile routes.
"""

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from bson.decimal128 import Decimal128
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_company, require_student
from app.core.database import get_db
from app.core.mongo import get_mongo_database
from app.models.student_profile import StudentProfile
from app.models.user import User, UserRole
from app.schemas.student_profile import (
    StudentProfileResponse,
    StudentSearchResult,
    StudentProfileUpdateRequest,
)


# group student profile endpoints under /api/students
router = APIRouter(
    prefix="/api/students",
    tags=["student profiles"],
)


def find_student_profile(
    current_user: User,
    db: Session,
) -> StudentProfile:
    """find the profile belonging to the logged-in student."""

    profile = db.scalar(
        select(StudentProfile).where(
            StudentProfile.user_id == current_user.id
        )
    )

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="student profile was not found",
        )

    return profile


def _mongo_profile_value(value: Any, field_name: str) -> Any:
    """convert Mongo scalar values to the existing profile response types."""

    if isinstance(value, Decimal128):
        return value.to_decimal()
    if field_name == "date_of_birth" and isinstance(value, datetime):
        return value.date()
    if isinstance(value, (date, datetime, Decimal)):
        return value
    return value


def mongo_profile_response(profile: dict[str, Any]) -> dict[str, Any]:
    """map one Mongo profile document to the full Lab 1 response shape."""

    fields = (
        "id",
        "user_id",
        "full_name",
        "college_name",
        "career_objective",
        "date_of_birth",
        "city",
        "state",
        "country",
        "degree",
        "major",
        "graduation_year",
        "cgpa",
        "experience",
        "skills",
        "phone",
        "profile_picture_url",
        "created_at",
        "updated_at",
    )
    result = {}
    for field_name in fields:
        value = profile.get(field_name)
        result[field_name] = _mongo_profile_value(value, field_name)
    result["id"] = int(result["id"])
    result["user_id"] = int(result["user_id"])
    return result


def mongo_search_result(profile: dict[str, Any]) -> dict[str, Any]:
    """map one Mongo profile to the company search response shape."""

    fields = (
        "id",
        "full_name",
        "college_name",
        "major",
        "skills",
        "city",
        "state",
        "degree",
        "graduation_year",
        "profile_picture_url",
    )
    result = {field_name: profile.get(field_name) for field_name in fields}
    result["id"] = int(result["id"])
    return result


def _get_profile_from_mongo(
    profile_id: int | None = None,
    user_id: int | None = None,
) -> tuple[bool, dict[str, Any] | None]:
    """return Mongo availability and one profile without exposing Mongo errors."""

    try:
        database = get_mongo_database()
        if database is None:
            return False, None
        query = {"id": profile_id} if profile_id is not None else {"user_id": user_id}
        profile = database["student_profiles"].find_one(query)
        return True, None if profile is None else mongo_profile_response(profile)
    except Exception:
        return False, None


def _search_students_from_mongo(
    name: str | None,
    college: str | None,
    major: str | None,
    skills: str | None,
) -> list[dict[str, Any]] | None:
    """search Mongo profiles or return none when SQL fallback is required."""

    try:
        database = get_mongo_database()
        if database is None:
            return None
        filters: dict[str, Any] = {}
        for field_name, value in (
            ("full_name", name),
            ("college_name", college),
            ("major", major),
            ("skills", skills),
        ):
            if isinstance(value, str) and value.strip():
                filters[field_name] = {
                    "$regex": re.escape(value.strip()),
                    "$options": "i",
                }
        cursor = database["student_profiles"].find(filters).sort("full_name", 1)
        return [mongo_search_result(profile) for profile in cursor]
    except Exception:
        return None


@router.get(
    "/me",
    response_model=StudentProfileResponse,
)
def get_my_student_profile(
    current_user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    """return the logged-in student's profile."""

    mongo_available, mongo_profile = _get_profile_from_mongo(user_id=current_user.id)
    if mongo_available:
        if mongo_profile is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="student profile was not found",
            )
        return mongo_profile

    return find_student_profile(current_user, db)


@router.put(
    "/me",
    response_model=StudentProfileResponse,
)
def update_my_student_profile(
    request: StudentProfileUpdateRequest,
    current_user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    """update only the profile fields sent by the student."""

    profile = find_student_profile(current_user, db)

    # exclude fields that were not included in the request
    updates = request.model_dump(exclude_unset=True)

    # apply each requested update to the profile
    for field_name, field_value in updates.items():
        setattr(profile, field_name, field_value)

    db.commit()
    db.refresh(profile)

    return profile


@router.get(
    "/search",
    response_model=list[StudentSearchResult],
)
def search_students(
    name: str | None = Query(default=None, max_length=100),
    college: str | None = Query(default=None, max_length=200),
    major: str | None = Query(default=None, max_length=150),
    skills: str | None = Query(default=None, max_length=200),
    current_user: User = Depends(require_company),
    db: Session = Depends(get_db),
):
    """search student profiles using company-approved filters."""

    mongo_profiles = _search_students_from_mongo(name, college, major, skills)
    if mongo_profiles is not None:
        return mongo_profiles

    statement = select(StudentProfile)
    filters = {
        "name": (StudentProfile.full_name, name),
        "college": (StudentProfile.college_name, college),
        "major": (StudentProfile.major, major),
        "skills": (StudentProfile.skills, skills),
    }

    # apply every supplied filter so companies can narrow their search
    for field_name, (column, value) in filters.items():
        if isinstance(value, str) and value.strip():
            statement = statement.where(column.ilike(f"%{value.strip()}%"))

    statement = statement.order_by(StudentProfile.full_name)
    return list(db.scalars(statement).all())


@router.get(
    "/{student_id}",
    response_model=StudentProfileResponse,
)
def get_student_profile(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """allow companies to view students and students to view only themselves."""

    mongo_available, mongo_profile = _get_profile_from_mongo(profile_id=student_id)
    if mongo_available:
        if mongo_profile is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="student profile was not found",
            )
        if (
            current_user.role == UserRole.STUDENT
            and mongo_profile["user_id"] != current_user.id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="students may only view their own profile",
            )
        return mongo_profile

    profile = db.get(StudentProfile, student_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="student profile was not found",
        )
    if current_user.role == UserRole.STUDENT and profile.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="students may only view their own profile",
        )
    return profile
