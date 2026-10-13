"""
test the five hand-built assistant tools with an isolated database.
"""

from datetime import datetime
from unittest import TestCase

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.assistant.tools import (
    get_job_details,
    get_student_preferences,
    save_job_or_event,
    search_events,
    search_jobs,
)
from app.core.database import Base
from app.models.event import Event
from app.models.job import Job
from app.models.student_profile import StudentProfile
from app.models.user import User, UserRole


class AssistantToolTests(TestCase):
    """verify the manual assistant tools without external services."""

    @classmethod
    def setUpClass(cls):
        # create one isolated database for the tool tests
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(cls.engine)

    def setUp(self):
        # create a fresh student and opportunity records for each test
        self.db = Session(self.engine)
        self.user = User(
            role=UserRole.STUDENT,
            email="assistant-test@example.com",
            password_hash="test-hash",
        )
        self.db.add(self.user)
        self.db.flush()
        self.student = StudentProfile(
            user_id=self.user.id,
            full_name="Assistant Test Student",
            college_name="Test College",
            major="Computer Science",
            skills="Python, SQL",
        )
        self.job = Job(
            title="Test Python Internship",
            description="Build a small Python service.",
            company_name="Test Labs",
            location="Sunnyvale office",
            city="Sunnyvale",
            employment_type="internship",
            is_remote=False,
            required_skills="Python, SQL",
            posted_at=datetime(2026, 10, 1, 9, 0),
        )
        self.event = Event(
            title="Test Data Workshop",
            description="Practice data skills with mentors.",
            organizer="Test Network",
            location="Online",
            city="Cupertino",
            event_date=datetime(2026, 10, 20, 18, 0),
            event_type="workshop",
            is_virtual=True,
        )
        self.db.add_all([self.student, self.job, self.event])
        self.db.commit()
        self.db.refresh(self.user)
        self.db.refresh(self.job)
        self.db.refresh(self.event)

    def tearDown(self):
        # clear isolated records before closing the session
        self.db.query(StudentProfile).delete()
        self.db.query(User).delete()
        self.db.query(Job).delete()
        self.db.query(Event).delete()
        self.db.commit()
        self.db.close()

    def test_get_student_preferences(self):
        """return the student's profile preferences."""

        preferences = get_student_preferences(self.db, self.user.id)

        self.assertEqual(preferences["major"], "Computer Science")
        self.assertEqual(preferences["skills"], "Python, SQL")

    def test_search_jobs_and_get_job_details(self):
        """find a job and retrieve its full details."""

        jobs = search_jobs(self.db, required_skill="Python")
        details = get_job_details(self.db, self.job.id)

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["id"], self.job.id)
        self.assertEqual(details["title"], "Test Python Internship")

    def test_search_events(self):
        """find events using city and virtual filters."""

        events = search_events(
            self.db,
            city="Cupertino",
            is_virtual=True,
        )

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["title"], "Test Data Workshop")

    def test_save_job_or_event_is_idempotent(self):
        """save both item types and report an existing save safely."""

        first_job_save = save_job_or_event(
            self.db,
            self.user.id,
            "job",
            self.job.id,
        )
        repeated_job_save = save_job_or_event(
            self.db,
            self.user.id,
            "job",
            self.job.id,
        )
        event_save = save_job_or_event(
            self.db,
            self.user.id,
            "event",
            self.event.id,
        )

        self.assertFalse(first_job_save["already_saved"])
        self.assertTrue(repeated_job_save["already_saved"])
        self.assertFalse(event_save["already_saved"])


if __name__ == "__main__":
    # run the tool tests directly without requiring a separate test runner
    import unittest

    unittest.main()
