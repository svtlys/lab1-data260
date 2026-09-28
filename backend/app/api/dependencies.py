"""
shared authentication and authorization dependencies.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User, UserRole


# tell FastAPI where clients obtain bearer tokens
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login",
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """decode the token and return the matching active user."""

    unauthorized_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="invalid or missing authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token_data = decode_access_token(token)
        user_id = int(token_data.get("sub", ""))
    except (ValueError, TypeError):
        raise unauthorized_error

    user = db.scalar(
        select(User).where(User.id == user_id)
    )

    if user is None or not user.is_active:
        raise unauthorized_error

    return user


def require_student(
    current_user: User = Depends(get_current_user),
) -> User:
    """allow only authenticated student users."""

    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="student access is required",
        )

    return current_user


def require_company(
    current_user: User = Depends(get_current_user),
) -> User:
    """allow only authenticated company users."""

    if current_user.role != UserRole.COMPANY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="company access is required",
        )

    return current_user