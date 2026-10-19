"""
test student profile lookup authorization.
"""

from unittest import TestCase

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.routes.student_profile import get_student_profile
from app.core.database import Base
from app.models.company_profile import CompanyProfile
from app.models.student_profile import StudentProfile
from app.models.user import User, UserRole


class StudentLookupTests(TestCase):
    """verify companies can view students and students stay scoped."""

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
        # create two students and one company
        self.db = Session(self.engine)
        self.student_user = User(
            role=UserRole.STUDENT,
            email="lookup-student@example.com",
            password_hash="test-hash",
        )
        self.other_student_user = User(
            role=UserRole.STUDENT,
            email="lookup-other-student@example.com",
            password_hash="test-hash",
        )
        self.company_user = User(
            role=UserRole.COMPANY,
            email="lookup-company@example.com",
            password_hash="test-hash",
        )
        self.db.add_all([self.student_user, self.other_student_user, self.company_user])
        self.db.flush()
        self.student = StudentProfile(
            user_id=self.student_user.id,
            full_name="Lookup Student",
            college_name="Test College",
        )
        self.other_student = StudentProfile(
            user_id=self.other_student_user.id,
            full_name="Other Student",
            college_name="Other College",
        )
        self.db.add_all([self.student, self.other_student])
        self.db.add(
            CompanyProfile(
                user_id=self.company_user.id,
                company_name="Lookup Company",
                location="Sunnyvale",
            )
        )
        self.db.commit()
        self.db.refresh(self.student)
        self.db.refresh(self.other_student)

    def tearDown(self):
        # remove test rows before closing the isolated session
        self.db.query(StudentProfile).delete()
        self.db.query(CompanyProfile).delete()
        self.db.query(User).delete()
        self.db.commit()
        self.db.close()

    def test_company_can_view_any_student(self):
        profile = get_student_profile(self.student.id, self.company_user, self.db)
        self.assertEqual(profile.full_name, "Lookup Student")

    def test_student_can_view_only_own_profile(self):
        profile = get_student_profile(self.student.id, self.student_user, self.db)
        self.assertEqual(profile.full_name, "Lookup Student")

        with self.assertRaises(HTTPException) as context:
            get_student_profile(self.other_student.id, self.student_user, self.db)
        self.assertEqual(context.exception.status_code, 403)


if __name__ == "__main__":
    import unittest

    unittest.main()
