"""
test the protected company profile routes.
"""

from unittest import TestCase

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import require_company
from app.api.routes.company import get_my_company_profile, update_my_company_profile
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


if __name__ == "__main__":
    import unittest

    unittest.main()
