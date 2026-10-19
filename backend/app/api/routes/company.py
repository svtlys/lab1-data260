"""
protected company profile routes.
"""

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
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

MAX_PROFILE_IMAGE_BYTES = 2 * 1024 * 1024
PROFILE_IMAGE_DIR = Path(__file__).resolve().parents[3] / "uploads" / "profile_images"
ALLOWED_PROFILE_IMAGES = {
    "image/jpeg": (".jpg", b"\xff\xd8\xff"),
    "image/png": (".png", b"\x89PNG\r\n\x1a\n"),
    "image/webp": (".webp", b"RIFF"),
}


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


async def read_profile_image(image: UploadFile) -> tuple[bytes, str]:
    """validate one image and return its bytes and safe extension."""

    image_type = image.content_type or ""
    image_details = ALLOWED_PROFILE_IMAGES.get(image_type)
    if image_details is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="profile picture must be JPEG, PNG, or WebP",
        )

    extension, signature = image_details
    filename = (image.filename or "").lower()
    if not filename.endswith(extension) and not (
        image_type == "image/jpeg" and filename.endswith(".jpeg")
    ):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="profile picture extension does not match its image type",
        )

    content = await image.read(MAX_PROFILE_IMAGE_BYTES + 1)
    if len(content) > MAX_PROFILE_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="profile picture must be 2 MB or smaller",
        )
    if not content.startswith(signature):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="profile picture content is not a valid image",
        )
    if image_type == "image/webp" and content[8:12] != b"WEBP":
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="profile picture content is not a valid WebP image",
        )

    return content, extension


@router.post(
    "/me/profile-picture",
    response_model=CompanyProfileResponse,
)
async def upload_company_profile_picture(
    request: Request,
    image: UploadFile = File(...),
    current_user: User = Depends(require_company),
    db: Session = Depends(get_db),
):
    """store a profile image for the logged-in company."""

    profile = find_company_profile(current_user, db)
    content, extension = await read_profile_image(image)
    PROFILE_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid4().hex}{extension}"
    stored_path = PROFILE_IMAGE_DIR / stored_name
    stored_path.write_bytes(content)

    old_url = profile.profile_picture_url
    profile.profile_picture_url = (
        f"{str(request.base_url).rstrip('/')}/api/companies/profile-images/{stored_name}"
    )
    try:
        db.commit()
        db.refresh(profile)
    except Exception:
        db.rollback()
        stored_path.unlink(missing_ok=True)
        raise

    # keep the previous file recoverable instead of deleting user data here
    _ = old_url
    return profile


@router.get(
    "/profile-images/{filename}",
)
def get_company_profile_picture(filename: str):
    """return a stored company logo by its generated filename."""

    image_directory = PROFILE_IMAGE_DIR.resolve()
    image_path = (image_directory / filename).resolve()
    if image_path.parent != image_directory or not image_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="profile picture was not found",
        )
    return FileResponse(image_path)
