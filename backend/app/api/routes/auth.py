"""
authentication routes for students and companies.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.company_profile import CompanyProfile
from app.models.student_profile import StudentProfile
from app.models.user import User, UserRole
from app.schemas.auth import (
    CompanySignupRequest,
    LoginRequest,
    StudentSignupRequest,
    TokenResponse,
    UserResponse,
)


# group authentication endpoints under /api/auth
router = APIRouter(
    prefix="/api/auth",
    tags=["authentication"],
)


@router.post(
    "/student/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def student_signup(
    request: StudentSignupRequest,
    db: Session = Depends(get_db),
):
    """create a student user and an empty student profile."""

    existing_user = db.scalar(
        select(User).where(User.email == request.email)
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="an account with this email already exists",
        )

    student_user = User(
        role=UserRole.STUDENT,
        email=request.email,
        password_hash=hash_password(request.password),
    )

    db.add(student_user)
    db.flush()

    student_profile = StudentProfile(
        user_id=student_user.id,
        full_name=request.full_name,
        college_name=request.college_name,
    )

    db.add(student_profile)

    try:
        db.commit()
        db.refresh(student_user)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="unable to create the student account",
        ) from error

    return student_user


@router.post(
    "/company/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def company_signup(
    request: CompanySignupRequest,
    db: Session = Depends(get_db),
):
    """create a company user and a company profile."""

    existing_user = db.scalar(
        select(User).where(User.email == request.email)
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="an account with this email already exists",
        )

    company_user = User(
        role=UserRole.COMPANY,
        email=request.email,
        password_hash=hash_password(request.password),
    )

    db.add(company_user)
    db.flush()

    company_profile = CompanyProfile(
        user_id=company_user.id,
        company_name=request.company_name,
        location=request.location,
    )

    db.add(company_profile)

    try:
        db.commit()
        db.refresh(company_user)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="unable to create the company account",
        ) from error

    return company_user


@router.post("/login", response_model=TokenResponse)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
):
    """verify credentials and return a JWT access token."""

    user = db.scalar(
        select(User).where(User.email == request.email)
    )

    if user is None or not verify_password(
        request.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="this account is inactive",
        )

    access_token = create_access_token(
        subject=str(user.id),
        role=user.role.value,
    )

    return TokenResponse(
        access_token=access_token,
        user=user,
    )


@router.post("/logout")
def logout():
    """
    complete client-side logout.

    JWT access tokens are stateless, so the frontend removes its
    stored token after receiving this response.
    """

    return {
        "message": "logout successful; remove the access token on the client",
    }