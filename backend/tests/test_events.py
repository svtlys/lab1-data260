"""
test the Week 3 event routes with an isolated in-memory database.
"""

from datetime import datetime
from unittest import TestCase

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.routes.events import (
    get_event_details,
    get_registered_events,
    register_for_event,
    search_events,
)
from app.core.database import Base
from app.models.event import Event
from app.models.event_registration import EventRegistration
from app.models.student_profile import StudentProfile
from app.models.user import User, UserRole


class EventRouteTests(TestCase):
    """verify the main student event workflows."""

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
        # create a fresh session and test data for each test
        self.db = Session(self.engine)
        self.user = User(
            role=UserRole.STUDENT,
            email="event-test@example.com",
            password_hash="test-hash",
        )
        self.db.add(self.user)
        self.db.flush()
        self.student = StudentProfile(
            user_id=self.user.id,
            full_name="Event Test Student",
            college_name="Test College",
        )
        self.db.add(self.student)
        self.events = [
            Event(
                title="Sunnyvale Career Fair",
                description="Meet local technology employers.",
                organizer="Career Network",
                location="Sunnyvale Civic Center",
                city="Sunnyvale",
                event_date=datetime(2026, 10, 17, 10, 0),
                event_type="career fair",
                is_virtual=False,
                capacity=100,
            ),
            Event(
                title="Cupertino Data Panel",
                description="Learn about data careers.",
                organizer="DATA 260 Alumni Group",
                location="Online",
                city="Cupertino",
                event_date=datetime(2026, 10, 28, 19, 0),
                event_type="panel",
                is_virtual=True,
                capacity=200,
            ),
        ]
        self.db.add_all(self.events)
        self.db.commit()
        self.db.refresh(self.user)
        self.db.refresh(self.student)
        self.db.refresh(self.events[0])
        self.db.refresh(self.events[1])

    def tearDown(self):
        # remove test rows before closing the isolated session
        self.db.query(EventRegistration).delete()
        self.db.query(Event).delete()
        self.db.query(StudentProfile).delete()
        self.db.query(User).delete()
        self.db.commit()
        self.db.close()

    def test_search_filters_by_city_and_virtual_format(self):
        """return only events that match the selected filters."""

        results = search_events(
            city="Cupertino",
            event_type=None,
            is_virtual=True,
            start_date=None,
            end_date=None,
            search=None,
            current_user=self.user,
            db=self.db,
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Cupertino Data Panel")

    def test_event_details_returns_not_found_for_unknown_event(self):
        """raise a 404 when the requested event does not exist."""

        with self.assertRaises(HTTPException) as context:
            get_event_details(99999, self.user, self.db)

        self.assertEqual(context.exception.status_code, 404)

    def test_registration_and_registered_events(self):
        """register a student and return the registered event."""

        registration = register_for_event(
            self.events[0].id,
            self.user,
            self.db,
        )
        registered_events = get_registered_events(self.user, self.db)

        self.assertEqual(registration.event_id, self.events[0].id)
        self.assertEqual(len(registered_events), 1)
        self.assertEqual(registered_events[0].title, "Sunnyvale Career Fair")

    def test_duplicate_registration_returns_conflict(self):
        """prevent the same student from registering twice."""

        register_for_event(self.events[0].id, self.user, self.db)

        with self.assertRaises(HTTPException) as context:
            register_for_event(self.events[0].id, self.user, self.db)

        self.assertEqual(context.exception.status_code, 409)


if __name__ == "__main__":
    # run the event tests directly without requiring a separate test runner
    import unittest

    unittest.main()
