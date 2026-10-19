"""
protected company profile routes.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_company
from app.core.database import get_db
from app.models.company_profile import CompanyProfile
from app.models.user import User
from app.schemas.company import CompanyProfileResponse, CompanyProfileUpdateRequest


# group company profile endpoints under /api/companies
router = APIRouter(
    prefix="/api/companies",
    tags=["company profiles"],
)


def find_company_profile(current_user: User, db: Session) -> CompanyProfile:
    """find the profile belonging to the logged-in company."""

    profile = db.scalar(
        select(CompanyProfile).where(
            CompanyProfile.user_id == current_user.id,
        )
    )

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="company profile was not found",
        )

    return profile


@router.get(
    "/me",
    response_model=CompanyProfileResponse,
)
def get_my_company_profile(
    current_user: User = Depends(require_company),
    db: Session = Depends(get_db),
):
    """return the logged-in company's profile."""

    return find_company_profile(current_user, db)


@router.put(
    "/me",
    response_model=CompanyProfileResponse,
)
def update_my_company_profile(
    request: CompanyProfileUpdateRequest,
    current_user: User = Depends(require_company),
    db: Session = Depends(get_db),
):
    """update only the company profile fields sent by the company."""

    profile = find_company_profile(current_user, db)
    updates = request.model_dump(exclude_unset=True)

    for field_name, field_value in updates.items():
        setattr(profile, field_name, field_value)

    db.commit()
    db.refresh(profile)

    return profile
