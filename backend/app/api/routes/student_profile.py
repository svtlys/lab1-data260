"""
protected student profile routes.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_student
from app.core.database import get_db
from app.models.student_profile import StudentProfile
from app.models.user import User, UserRole
from app.schemas.student_profile import (
    StudentProfileResponse,
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


@router.get(
    "/me",
    response_model=StudentProfileResponse,
)
def get_my_student_profile(
    current_user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    """return the logged-in student's profile."""

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
    "/{student_id}",
    response_model=StudentProfileResponse,
)
def get_student_profile(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """allow companies to view students and students to view only themselves."""

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
