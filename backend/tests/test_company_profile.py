"""
test the protected company profile routes.
"""

import asyncio
from io import BytesIO
from pathlib import Path
from unittest import TestCase

from fastapi import HTTPException, UploadFile
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from starlette.datastructures import Headers
from starlette.requests import Request

from app.api.dependencies import get_current_user, require_company
from app.api.routes.company import (
    MAX_PROFILE_IMAGE_BYTES,
    PROFILE_IMAGE_DIR,
    get_my_company_profile,
    update_my_company_profile,
    upload_company_profile_picture,
)
from app.core.database import Base
from app.models.company_profile import CompanyProfile
from app.models.user import User, UserRole
from app.schemas.company import CompanyProfileUpdateRequest


class CompanyProfileRouteTests(TestCase):
    """verify company profile access and ownership."""

    @classmethod
    def setUpClass(cls):
        # create one shared in-memory database for this test class
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(cls.engine)

    def setUp(self):
        # create one company and one student for each test
        self.db = Session(self.engine)
        self.company_user = User(
            role=UserRole.COMPANY,
            email="company-profile-test@example.com",
            password_hash="test-hash",
        )
        self.student_user = User(
            role=UserRole.STUDENT,
            email="company-profile-student@example.com",
            password_hash="test-hash",
        )
        self.db.add_all([self.company_user, self.student_user])
        self.db.flush()
        self.profile = CompanyProfile(
            user_id=self.company_user.id,
            company_name="Test Company",
            location="Sunnyvale",
        )
        self.db.add(self.profile)
        self.db.commit()
        self.db.refresh(self.company_user)
        self.db.refresh(self.student_user)
        self.db.refresh(self.profile)

    def tearDown(self):
        # remove test rows before closing the isolated session
        for path in PROFILE_IMAGE_DIR.glob("test-profile-*.png"):
            path.unlink(missing_ok=True)
        self.db.query(CompanyProfile).delete()
        self.db.query(User).delete()
        self.db.commit()
        self.db.close()

    def test_company_can_read_and_update_own_profile(self):
        profile = get_my_company_profile(self.company_user, self.db)
        self.assertEqual(profile.company_name, "Test Company")

        updated = update_my_company_profile(
            CompanyProfileUpdateRequest(
                description="A local technology company.",
                contact_phone="408-555-0100",
            ),
            self.company_user,
            self.db,
        )

        self.assertEqual(updated.description, "A local technology company.")
        self.assertEqual(updated.contact_phone, "408-555-0100")
        self.assertEqual(updated.location, "Sunnyvale")

    def test_student_cannot_read_company_profile(self):
        with self.assertRaises(HTTPException) as context:
            require_company(self.student_user)

        self.assertEqual(context.exception.status_code, 403)

    def test_company_can_upload_valid_profile_picture(self):
        image = UploadFile(
            file=BytesIO(b"\x89PNG\r\n\x1a\nvalid test image"),
            filename="test-profile-valid.png",
            headers=Headers({"content-type": "image/png"}),
        )
        request = Request(
            {
                "type": "http",
                "method": "POST",
                "scheme": "http",
                "server": ("127.0.0.1", 9160),
                "path": "/api/companies/me/profile-picture",
                "headers": [],
            }
        )

        profile = asyncio.run(
            upload_company_profile_picture(
                request=request,
                image=image,
                current_user=self.company_user,
                db=self.db,
            )
        )

        self.assertIn("/api/companies/profile-images/", profile.profile_picture_url)
        stored_name = profile.profile_picture_url.rsplit("/", 1)[-1]
        stored_path = PROFILE_IMAGE_DIR / stored_name
        self.assertTrue(stored_path.is_file())
        stored_path.unlink(missing_ok=True)

    def test_invalid_profile_picture_type_is_rejected(self):
        image = UploadFile(
            file=BytesIO(b"not an image"),
            filename="test-profile.txt",
            headers=Headers({"content-type": "text/plain"}),
        )

        with self.assertRaises(HTTPException) as context:
            asyncio.run(
                upload_company_profile_picture(
                    request=self.make_request(),
                    image=image,
                    current_user=self.company_user,
                    db=self.db,
                )
            )

        self.assertEqual(context.exception.status_code, 415)

    def test_oversized_profile_picture_is_rejected(self):
        image = UploadFile(
            file=BytesIO(b"\x89PNG\r\n\x1a\n" + b"x" * MAX_PROFILE_IMAGE_BYTES),
            filename="test-profile-large.png",
            headers=Headers({"content-type": "image/png"}),
        )

        with self.assertRaises(HTTPException) as context:
            asyncio.run(
                upload_company_profile_picture(
                    request=self.make_request(),
                    image=image,
                    current_user=self.company_user,
                    db=self.db,
                )
            )

        self.assertEqual(context.exception.status_code, 413)

    def test_unauthenticated_upload_is_rejected(self):
        with self.assertRaises(HTTPException) as context:
            get_current_user(token="", db=self.db)

        self.assertEqual(context.exception.status_code, 401)

    def test_student_cannot_upload_company_profile_picture(self):
        with self.assertRaises(HTTPException) as context:
            require_company(self.student_user)

        self.assertEqual(context.exception.status_code, 403)

    @staticmethod
    def make_request():
        return Request(
            {
                "type": "http",
                "method": "POST",
                "scheme": "http",
                "server": ("127.0.0.1", 9160),
                "path": "/api/companies/me/profile-picture",
                "headers": [],
            }
        )


if __name__ == "__main__":
    import unittest

    unittest.main()
