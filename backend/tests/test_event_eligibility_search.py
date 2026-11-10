"""
test the assistant's event search eligibility filter and the date prompt line.
"""

from datetime import datetime
import json
from unittest import TestCase

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.assistant.loop import _system_prompt
from app.assistant.tools import search_events
from app.core.database import Base
from app.models.event import Event


def _event(title, majors):
    """build one event for the eligibility tests."""

    return Event(
        title=title,
        description="Test event.",
        organizer="Test Organizer",
        location="Sunnyvale",
        city="Sunnyvale",
        event_date=datetime(2026, 11, 20, 18, 0),
        event_type="Workshop",
        is_virtual=False,
        capacity=20,
        eligible_majors=majors,
    )


class EventEligibilitySearchTests(TestCase):
    """verify the major filter and the date line in the system prompt."""

    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(cls.engine)

    def setUp(self):
        self.db = Session(self.engine)
        self.db.add_all(
            [
                _event("CS Night", "Computer Science, Data Science"),
                _event("Business Mixer", "Business"),
                _event("Open Workshop", None),
            ]
        )
        self.db.commit()

    def tearDown(self):
        self.db.query(Event).delete()
        self.db.commit()
        self.db.close()

    def test_major_filter_keeps_matching_and_open_events(self):
        """return events open to the major plus events with no major list."""

        rows = json.loads(search_events(self.db, major="Computer Science"))
        titles = sorted(row["title"] for row in rows)

        self.assertEqual(titles, ["CS Night", "Open Workshop"])
        self.assertIn("eligible_majors", rows[0])

    def test_system_prompt_includes_todays_date(self):
        """tell the model today's date so next month can be resolved."""

        self.assertIn("today's date is 20", _system_prompt())
