"""
the five required Week 3 assistant tool tests.
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
from app.models.saved_item import SavedItem
from app.models.student_profile import StudentProfile
from app.models.user import User, UserRole


class RequiredAssistantTests(TestCase):
    """verify exactly one required test for each assistant tool."""

    @classmethod
    def setUpClass(cls):
        # create an isolated database for the required tool tests
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(cls.engine)

    def setUp(self):
        # create predictable student, job, and event records
        self.db = Session(self.engine)
        self.user = User(
            role=UserRole.STUDENT,
            email="required-tools@example.com",
            password_hash="test-hash",
        )
        self.student = StudentProfile(
            user=self.user,
            full_name="Required Tools Student",
            college_name="Test College",
            major="Computer Science",
            skills="Python, SQL",
        )
        self.job = Job(
            title="Required Python Job",
            description="Build a Python service for students.",
            company_name="Required Labs",
            location="Sunnyvale office",
            city="Sunnyvale",
            employment_type="internship",
            is_remote=False,
            required_skills="Python, SQL",
            posted_at=datetime(2026, 10, 1, 9, 0),
        )
        self.event = Event(
            title="Required Data Event",
            description="Learn practical data skills.",
            organizer="Required Network",
            location="Online",
            city="Cupertino",
            event_date=datetime(2026, 10, 20, 18, 0),
            event_type="workshop",
            is_virtual=True,
        )
        self.db.add_all([self.user, self.student, self.job, self.event])
        self.db.commit()
        self.db.refresh(self.user)
        self.db.refresh(self.job)
        self.db.refresh(self.event)

    def tearDown(self):
        # remove saved rows before their referenced records
        self.db.query(SavedItem).delete()
        self.db.query(StudentProfile).delete()
        self.db.query(User).delete()
        self.db.query(Job).delete()
        self.db.query(Event).delete()
        self.db.commit()
        self.db.close()

    def test_get_student_preferences(self):
        """verify the assistant can read student preferences."""

        result = get_student_preferences(self.db, self.user.id)

        self.assertEqual(result["major"], "Computer Science")

    def test_search_jobs(self):
        """verify the assistant can search jobs by skill."""

        result = search_jobs(self.db, required_skill="Python")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], self.job.id)

    def test_get_job_details(self):
        """verify the assistant can retrieve one job."""

        result = get_job_details(self.db, self.job.id)

        self.assertEqual(result["title"], "Required Python Job")

    def test_search_events(self):
        """verify the assistant can search virtual events."""

        result = search_events(self.db, is_virtual=True)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Required Data Event")

    def test_save_job_or_event(self):
        """verify the assistant can save one job or event."""

        result = save_job_or_event(
            self.db,
            self.user.id,
            "event",
            self.event.id,
        )

        self.assertTrue(result["saved"])
        self.assertFalse(result["already_saved"])


if __name__ == "__main__":
    # run the five required tests directly without another test runner
    import unittest

    unittest.main()
