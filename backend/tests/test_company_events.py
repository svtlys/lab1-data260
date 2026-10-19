"""
test company event ownership and registration views.
"""

from datetime import datetime
from unittest import TestCase

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.routes.company_events import (
    create_company_event,
    get_event_registrations,
    get_my_company_events,
)
from app.api.routes.events import register_for_event
from app.core.database import Base
from app.models.company_profile import CompanyProfile
from app.models.event import Event
from app.models.event_registration import EventRegistration
from app.models.student_profile import StudentProfile
from app.models.user import User, UserRole
from app.schemas.company_event import CompanyEventCreateRequest


class CompanyEventRouteTests(TestCase):
    """verify company event ownership and eligibility reporting."""

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
        # create one company, one student, and one registered event
        self.db = Session(self.engine)
        self.company_user = User(
            role=UserRole.COMPANY,
            email="event-company@example.com",
            password_hash="test-hash",
        )
        self.student_user = User(
            role=UserRole.STUDENT,
            email="event-student@example.com",
            password_hash="test-hash",
        )
        self.db.add_all([self.company_user, self.student_user])
        self.db.flush()
        self.company = CompanyProfile(
            user_id=self.company_user.id,
            company_name="Event Company",
            location="Mountain View",
        )
        self.student = StudentProfile(
            user_id=self.student_user.id,
            full_name="Event Student",
            college_name="Test College",
            major="History",
            cgpa=2.5,
            graduation_year=2030,
        )
        self.db.add_all([self.company, self.student])
        self.db.flush()
        self.event = Event(
            company_id=self.company.id,
            title="Data Workshop",
            description="Learn data skills.",
            organizer="Event Company",
            location="Mountain View Hall",
            city="Mountain View",
            event_date=datetime(2030, 10, 20, 10, 0),
            event_type="Workshop",
            is_virtual=False,
            capacity=20,
            eligible_majors="Data Analytics",
            min_cgpa=3.0,
            min_grad_year=2027,
        )
        self.db.add(self.event)
        self.db.commit()
        self.db.refresh(self.event)

    def tearDown(self):
        # remove test rows before closing the isolated session
        self.db.query(EventRegistration).delete()
        self.db.query(Event).delete()
        self.db.query(StudentProfile).delete()
        self.db.query(CompanyProfile).delete()
        self.db.query(User).delete()
        self.db.commit()
        self.db.close()

    def test_company_can_create_and_list_own_events(self):
        created = create_company_event(
            CompanyEventCreateRequest(
                title="Career Fair",
                description="Meet employers.",
                event_type="Career Fair",
                city="Sunnyvale",
                location="Civic Center",
                event_date=datetime(2030, 11, 1, 10, 0),
                capacity=50,
            ),
            self.company_user,
            self.db,
        )
        events = get_my_company_events(self.company_user, self.db)

        self.assertEqual(created["company_id"], self.company.id)
        self.assertEqual(len(events), 2)

    def test_company_can_view_registered_students_and_eligibility(self):
        self.db.add(
            EventRegistration(
                event_id=self.event.id,
                student_id=self.student.id,
            )
        )
        self.db.commit()

        registrations = get_event_registrations(self.event.id, self.company_user, self.db)

        self.assertEqual(len(registrations), 1)
        self.assertFalse(registrations[0]["eligible"])
        self.assertEqual(len(registrations[0]["ineligible_reasons"]), 2)

    def test_student_cannot_use_company_event_route(self):
        with self.assertRaises(HTTPException) as context:
            get_my_company_events(self.student_user, self.db)

        self.assertEqual(context.exception.status_code, 404)

    def test_company_event_registration_checks_eligibility(self):
        with self.assertRaises(HTTPException) as context:
            register_for_event(self.event.id, self.student_user, self.db)
        self.assertEqual(context.exception.status_code, 403)

        self.student.major = "Data Analytics"
        self.student.cgpa = 3.5
        self.db.commit()
        registration = register_for_event(self.event.id, self.student_user, self.db)
        self.assertEqual(registration.event_id, self.event.id)


if __name__ == "__main__":
    import unittest

    unittest.main()
