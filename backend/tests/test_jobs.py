"""
test student job browsing and company job posting routes.
"""

from datetime import date, datetime
from unittest import TestCase

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import require_company, require_student
from app.api.routes.jobs import create_job, get_job_details, get_my_jobs, search_jobs
from app.core.database import Base
from app.models.company_profile import CompanyProfile
from app.models.job import Job
from app.models.user import User, UserRole
from app.schemas.job import EMPLOYMENT_TYPE_VALUES, JobCreateRequest


class JobRouteTests(TestCase):
    """verify job ownership and student browsing."""

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
        # create two companies and one student for ownership tests
        self.db = Session(self.engine)
        self.company_user = User(
            role=UserRole.COMPANY,
            email="job-company@example.com",
            password_hash="test-hash",
        )
        self.other_company_user = User(
            role=UserRole.COMPANY,
            email="job-other-company@example.com",
            password_hash="test-hash",
        )
        self.student_user = User(
            role=UserRole.STUDENT,
            email="job-student@example.com",
            password_hash="test-hash",
        )
        self.db.add_all([self.company_user, self.other_company_user, self.student_user])
        self.db.flush()
        self.company_profile = CompanyProfile(
            user_id=self.company_user.id,
            company_name="First Company",
            location="Sunnyvale",
        )
        self.other_profile = CompanyProfile(
            user_id=self.other_company_user.id,
            company_name="Second Company",
            location="Cupertino",
        )
        self.db.add_all([self.company_profile, self.other_profile])
        self.db.flush()
        # create one fixture for every canonical employment type
        self.db.add_all(
            [
                Job(
                    company_id=self.company_profile.id,
                    title="Data Intern",
                    description="Work with data pipelines and reports.",
                    company_name="First Company",
                    location="Sunnyvale, CA",
                    city="Sunnyvale",
                    employment_type="Internship",
                    is_remote=False,
                    required_skills="Python, SQL",
                    posted_at=datetime(2026, 10, 1),
                    deadline=date(2026, 12, 1),
                ),
                Job(
                    company_id=self.company_profile.id,
                    title="Data Engineer",
                    description="Build production data pipelines.",
                    company_name="First Company",
                    location="Cupertino, CA",
                    city="Cupertino",
                    employment_type="Full-time",
                    is_remote=False,
                    required_skills="Python, SQL",
                    posted_at=datetime(2026, 10, 2),
                ),
                Job(
                    company_id=self.company_profile.id,
                    title="Part-time Analyst",
                    description="Support weekly business reports.",
                    company_name="First Company",
                    location="Mountain View, CA",
                    city="Mountain View",
                    employment_type="Part-time",
                    is_remote=True,
                    required_skills="Excel",
                    posted_at=datetime(2026, 10, 3),
                ),
                Job(
                    company_id=self.company_profile.id,
                    title="Campus Data Assistant",
                    description="Help maintain campus data systems.",
                    company_name="First Company",
                    location="Sunnyvale, CA",
                    city="Sunnyvale",
                    employment_type="On-campus",
                    is_remote=False,
                    required_skills="Data entry",
                    posted_at=datetime(2026, 10, 4),
                ),
            ]
        )
        self.db.commit()
        self.db.refresh(self.company_user)
        self.db.refresh(self.other_company_user)
        self.db.refresh(self.student_user)

    def tearDown(self):
        # remove test rows before closing the isolated session
        self.db.query(Job).delete()
        self.db.query(CompanyProfile).delete()
        self.db.query(User).delete()
        self.db.commit()
        self.db.close()

    def test_company_can_create_and_list_only_own_jobs(self):
        created = create_job(
            JobCreateRequest(
                title="Analytics Intern",
                description="Build dashboards for local teams.",
                employment_type="Internship",
                city="Sunnyvale",
                deadline=date(2026, 12, 15),
            ),
            self.company_user,
            self.db,
        )
        jobs = get_my_jobs(self.company_user, self.db)

        self.assertEqual(created["company_id"], self.company_profile.id)
        self.assertEqual(len(jobs), 5)
        self.assertTrue(all(job["company_id"] == self.company_profile.id for job in jobs))

    def test_student_can_filter_each_canonical_employment_type(self):
        for employment_type in EMPLOYMENT_TYPE_VALUES:
            jobs = search_jobs(
                search=None,
                city=None,
                employment_type=employment_type,
                is_remote=None,
                current_user=self.student_user,
                db=self.db,
            )

            self.assertTrue(jobs)
            self.assertTrue(all(job["employment_type"] == employment_type for job in jobs))

    def test_employment_type_filter_preserves_city_filter(self):
        jobs = search_jobs(
            search=None,
            city="Mountain View",
            employment_type="Part-time",
            is_remote=None,
            current_user=self.student_user,
            db=self.db,
        )

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["city"], "Mountain View")
        self.assertEqual(jobs[0]["employment_type"], "Part-time")

    def test_student_can_search_and_view_job_details(self):
        jobs = search_jobs(
            search="Python",
            city="Sunnyvale",
            employment_type=None,
            is_remote=None,
            current_user=self.student_user,
            db=self.db,
        )
        details = get_job_details(jobs[0]["id"], self.student_user, self.db)

        self.assertEqual(len(jobs), 1)
        self.assertEqual(details["title"], "Data Intern")

    def test_role_guards_reject_wrong_users(self):
        with self.assertRaises(HTTPException) as company_error:
            require_company(self.student_user)
        with self.assertRaises(HTTPException) as student_error:
            require_student(self.company_user)

        self.assertEqual(company_error.exception.status_code, 403)
        self.assertEqual(student_error.exception.status_code, 403)


if __name__ == "__main__":
    import unittest

    unittest.main()
