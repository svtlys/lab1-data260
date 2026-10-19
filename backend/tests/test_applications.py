"""
test job application ownership, status, duplicate, and PDF behavior.
"""

import asyncio
from datetime import datetime
from io import BytesIO
from pathlib import Path
from unittest import TestCase

from fastapi import HTTPException, UploadFile
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from starlette.datastructures import Headers

from app.api.routes.applications import (
    apply_to_job,
    get_job_applications,
    get_my_applications,
    read_pdf_resume,
    update_application_status,
)
from app.core.database import Base
from app.models.application import Application
from app.models.company_profile import CompanyProfile
from app.models.job import Job
from app.models.student_profile import StudentProfile
from app.models.user import User, UserRole
from app.schemas.application import ApplicationStatusUpdateRequest


class ApplicationRouteTests(TestCase):
    """verify student and company application permissions."""

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
        # create two companies, one student, and one job
        self.db = Session(self.engine)
        self.company_user = User(
            role=UserRole.COMPANY,
            email="application-company@example.com",
            password_hash="test-hash",
        )
        self.other_company_user = User(
            role=UserRole.COMPANY,
            email="application-other-company@example.com",
            password_hash="test-hash",
        )
        self.student_user = User(
            role=UserRole.STUDENT,
            email="application-student@example.com",
            password_hash="test-hash",
        )
        self.db.add_all([self.company_user, self.other_company_user, self.student_user])
        self.db.flush()
        self.company_profile = CompanyProfile(
            user_id=self.company_user.id,
            company_name="Application Company",
            location="Sunnyvale",
        )
        self.other_profile = CompanyProfile(
            user_id=self.other_company_user.id,
            company_name="Other Company",
            location="Cupertino",
        )
        self.student_profile = StudentProfile(
            user_id=self.student_user.id,
            full_name="Application Student",
            college_name="Test College",
            major="Data Analytics",
        )
        self.db.add_all([self.company_profile, self.other_profile, self.student_profile])
        self.db.flush()
        self.job = Job(
            company_id=self.company_profile.id,
            title="Data Analyst",
            description="Analyze reports for local teams.",
            company_name="Application Company",
            location="Sunnyvale, CA",
            city="Sunnyvale",
            employment_type="Full-time",
            is_remote=False,
            posted_at=datetime(2026, 10, 1),
        )
        self.db.add(self.job)
        self.db.commit()
        self.db.refresh(self.job)
        self.created_paths = []

    def tearDown(self):
        # remove uploaded test files and database rows
        for path in self.created_paths:
            Path(path).unlink(missing_ok=True)
        self.db.query(Application).delete()
        self.db.query(Job).delete()
        self.db.query(StudentProfile).delete()
        self.db.query(CompanyProfile).delete()
        self.db.query(User).delete()
        self.db.commit()
        self.db.close()

    def make_pdf_upload(self, filename="resume.pdf"):
        return UploadFile(
            file=BytesIO(b"%PDF-1.7 test resume"),
            filename=filename,
            headers=Headers({"content-type": "application/pdf"}),
        )

    def test_student_can_apply_with_pdf_and_view_own_application(self):
        application_data = asyncio.run(
            apply_to_job(
                self.job.id,
                resume=self.make_pdf_upload(),
                current_user=self.student_user,
                db=self.db,
            )
        )
        applications = get_my_applications(self.student_user, self.db)
        stored_path = self.db.get(Application, application_data["id"]).resume_path
        self.created_paths.append(stored_path)

        self.assertEqual(application_data["status"], "Pending")
        self.assertEqual(application_data["resume_filename"], "resume.pdf")
        self.assertEqual(len(applications), 1)

    def test_duplicate_application_is_rejected(self):
        asyncio.run(
            apply_to_job(
                self.job.id,
                resume=None,
                current_user=self.student_user,
                db=self.db,
            )
        )

        with self.assertRaises(HTTPException) as context:
            asyncio.run(
                apply_to_job(
                    self.job.id,
                    resume=None,
                    current_user=self.student_user,
                    db=self.db,
                )
            )

        self.assertEqual(context.exception.status_code, 409)

    def test_company_can_review_owned_application_but_other_company_cannot(self):
        asyncio.run(
            apply_to_job(
                self.job.id,
                resume=None,
                current_user=self.student_user,
                db=self.db,
            )
        )
        application = self.db.query(Application).one()

        applicants = get_job_applications(self.job.id, self.company_user, self.db)
        self.assertEqual(len(applicants), 1)
        updated = update_application_status(
            application.id,
            ApplicationStatusUpdateRequest(status="Reviewed"),
            self.company_user,
            self.db,
        )
        self.assertEqual(updated["status"], "Reviewed")

        with self.assertRaises(HTTPException) as context:
            get_job_applications(self.job.id, self.other_company_user, self.db)
        self.assertEqual(context.exception.status_code, 404)

    def test_non_pdf_upload_is_rejected(self):
        with self.assertRaises(HTTPException) as context:
            asyncio.run(read_pdf_resume(self.make_pdf_upload("resume.txt")))

        self.assertEqual(context.exception.status_code, 415)


if __name__ == "__main__":
    import unittest

    unittest.main()
