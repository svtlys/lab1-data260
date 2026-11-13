"""
test the Week 3 event routes with an isolated in-memory database.
"""

import json
from datetime import datetime, timezone
from unittest import TestCase
from unittest.mock import patch

from fastapi import HTTPException
from starlette.requests import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.routes.events import (
    get_event_details,
    get_registered_events,
    register_for_event,
    search_events,
)
from app.core.config import settings
from app.core.database import Base
from app.models.event import Event
from app.models.event_registration import EventRegistration
from app.models.student_profile import StudentProfile
from app.models.user import User, UserRole
from app.schemas.event import EventResponse


class FakeMongoCursor:
    def __init__(self, documents):
        self.documents = list(documents)

    def sort(self, field, direction):
        return FakeMongoCursor(
            sorted(
                self.documents,
                key=lambda document: document.get(field),
                reverse=direction < 0,
            )
        )

    def __iter__(self):
        return iter(self.documents)


class FakeMongoCollection:
    def __init__(self, documents):
        self.documents = list(documents)

    @staticmethod
    def matches(document, query):
        for field, expected in query.items():
            if field == "$or":
                if not any(FakeMongoCollection.matches(document, branch) for branch in expected):
                    return False
                continue
            actual = document.get(field)
            if isinstance(expected, dict) and "$regex" in expected:
                import re

                flags = re.IGNORECASE if "i" in expected.get("$options", "") else 0
                if re.search(expected["$regex"], str(actual or ""), flags) is None:
                    return False
            elif isinstance(expected, dict) and "$gte" in expected:
                if actual < expected["$gte"]:
                    return False
                if "$lte" in expected and actual > expected["$lte"]:
                    return False
            elif isinstance(expected, dict) and "$lte" in expected:
                if actual > expected["$lte"]:
                    return False
            elif actual != expected:
                return False
        return True

    def find(self, query):
        return FakeMongoCursor(
            [document for document in self.documents if self.matches(document, query)]
        )

    def find_one(self, query):
        return next(iter(self.find(query)), None)


class FakeMongoDatabase:
    def __init__(self, events, registrations=None, profiles=None):
        self.collections = {
            "events": FakeMongoCollection(events),
            "event_registrations": FakeMongoCollection(registrations or []),
            "student_profiles": FakeMongoCollection(profiles or []),
        }

    def __getitem__(self, collection):
        return self.collections[collection]


class FakeKafkaFuture:
    def get(self, timeout):
        return None


class FakeKafkaProducer:
    def __init__(self, events):
        self.events = events

    def send(self, topic, key, value):
        self.events.append((topic, key, value))
        return FakeKafkaFuture()


class FailingKafkaProducer:
    def send(self, topic, key, value):
        raise RuntimeError("broker failure details")


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
        self.original_kafka_enabled = settings.kafka_enabled
        settings.kafka_enabled = False
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
        settings.kafka_enabled = self.original_kafka_enabled

    def make_request(self, trace_id=None):
        headers = []
        if trace_id:
            headers.append((b"x-trace-id", trace_id.encode()))
        return Request(
            {
                "type": "http",
                "method": "POST",
                "scheme": "http",
                "server": ("127.0.0.1", 9160),
                "path": f"/api/events/{self.events[0].id}/register",
                "headers": headers,
            }
        )

    def migrated_event_documents(self):
        return [
            {
                "id": event.id,
                "company_id": event.company_id,
                "title": event.title,
                "description": event.description,
                "organizer": event.organizer,
                "location": event.location,
                "city": event.city,
                "event_date": event.event_date,
                "event_type": event.event_type,
                "is_virtual": event.is_virtual,
                "capacity": event.capacity,
                "eligible_majors": event.eligible_majors,
                "min_cgpa": event.min_cgpa,
                "min_grad_year": event.min_grad_year,
                "max_grad_year": event.max_grad_year,
                "eligibility_note": event.eligibility_note,
                "created_at": event.created_at,
                "updated_at": event.updated_at,
            }
            for event in self.events
        ]

    def migrated_student_documents(self):
        return [{"id": self.student.id, "user_id": self.student.user_id}]

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

    def test_mongo_event_search_matches_mysql_response(self):
        mysql_results = [
            EventResponse.model_validate(event).model_dump()
            for event in search_events(
                city="Cupertino",
                event_type="panel",
                is_virtual=True,
                start_date=datetime(2026, 10, 1),
                end_date=datetime(2026, 11, 1),
                search="data",
                current_user=self.user,
                db=self.db,
            )
        ]
        database = FakeMongoDatabase(self.migrated_event_documents())

        with patch(
            "app.api.routes.events.get_mongo_database",
            return_value=database,
        ):
            mongo_results = search_events(
                city="Cupertino",
                event_type="panel",
                is_virtual=True,
                start_date=datetime(2026, 10, 1),
                end_date=datetime(2026, 11, 1),
                search="data",
                current_user=self.user,
                db=self.db,
            )

        self.assertEqual(mongo_results, mysql_results)
        self.assertNotIn("_id", mongo_results[0])

    def test_mongo_event_details_and_registered_listing_match_mysql(self):
        registration = register_for_event(self.events[0].id, self.user, self.db)
        mysql_detail = EventResponse.model_validate(
            get_event_details(self.events[0].id, self.user, self.db)
        ).model_dump()
        mysql_registered = [
            EventResponse.model_validate(event).model_dump()
            for event in get_registered_events(self.user, self.db)
        ]
        database = FakeMongoDatabase(
            self.migrated_event_documents(),
            registrations=[
                {
                    "id": registration.id,
                    "event_id": registration.event_id,
                    "student_id": registration.student_id,
                    "registered_at": registration.registered_at,
                }
            ],
            profiles=self.migrated_student_documents(),
        )

        with patch(
            "app.api.routes.events.get_mongo_database",
            return_value=database,
        ):
            mongo_detail = get_event_details(self.events[0].id, self.user, self.db)
            mongo_registered = get_registered_events(self.user, self.db)

        self.assertEqual(mongo_detail, mysql_detail)
        self.assertEqual(mongo_registered, mysql_registered)

    def test_event_reads_fall_back_to_mysql_when_mongo_is_unavailable(self):
        with patch(
            "app.api.routes.events.get_mongo_database",
            side_effect=RuntimeError("mongo unavailable"),
        ):
            results = search_events(
                city=None,
                event_type=None,
                is_virtual=None,
                start_date=None,
                end_date=None,
                search=None,
                current_user=self.user,
                db=self.db,
            )

        self.assertEqual([event.id for event in results], [self.events[0].id, self.events[1].id])

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

    def test_registration_kafka_disabled_skips_publish_and_preserves_response(self):
        events = []
        producer = FakeKafkaProducer(events)
        with patch(
            "app.messaging.producer.get_kafka_producer",
            return_value=producer,
        ) as get_producer:
            registration = register_for_event(
                self.events[0].id,
                self.user,
                self.db,
                self.make_request(),
            )

        get_producer.assert_not_called()
        self.assertEqual(registration.event_id, self.events[0].id)
        self.assertEqual(registration.student_id, self.student.id)
        self.assertEqual(events, [])

    def test_registration_event_metadata_and_payload_are_correct(self):
        settings.kafka_enabled = True
        events = []
        producer = FakeKafkaProducer(events)
        trace_id = "11111111-1111-4111-8111-111111111111"
        with patch(
            "app.messaging.producer.get_kafka_producer",
            return_value=producer,
        ):
            registration = register_for_event(
                self.events[0].id,
                self.user,
                self.db,
                self.make_request(trace_id),
            )

        self.assertEqual(len(events), 1)
        topic, key, value = events[0]
        message = json.loads(value)
        self.assertEqual(topic, "p16.event.registration_created")
        self.assertEqual(key, str(self.events[0].id))
        self.assertEqual(message["event_type"], "event.registration_created")
        self.assertEqual(message["trace_id"], trace_id)
        self.assertEqual(
            message["actor"],
            {"user_id": self.user.id, "role": "student"},
        )
        self.assertEqual(
            message["payload"],
            {
                "registration_id": registration.id,
                "event_id": self.events[0].id,
                "student_id": self.student.id,
                "registered_at": registration.registered_at.replace(
                    tzinfo=timezone.utc
                ).isoformat().replace("+00:00", "Z"),
            },
        )

    def test_registration_commits_before_publish(self):
        settings.kafka_enabled = True
        order = []
        original_commit = self.db.commit

        def commit_then_record():
            original_commit()
            order.append("commit")

        producer = FakeKafkaProducer(order)
        with patch.object(self.db, "commit", side_effect=commit_then_record), patch(
            "app.messaging.producer.get_kafka_producer",
            return_value=producer,
        ):
            registration = register_for_event(
                self.events[0].id,
                self.user,
                self.db,
                self.make_request(),
            )

        self.assertEqual(registration.event_id, self.events[0].id)
        self.assertEqual(order[0], "commit")
        self.assertEqual(order[1][0], "p16.event.registration_created")
        self.assertEqual(order[1][1], str(self.events[0].id))

    def test_registration_publish_failure_preserves_commit_and_response(self):
        settings.kafka_enabled = True
        with patch(
            "app.messaging.producer.get_kafka_producer",
            return_value=FailingKafkaProducer(),
        ):
            registration = register_for_event(
                self.events[0].id,
                self.user,
                self.db,
                self.make_request(),
            )

        self.assertEqual(registration.event_id, self.events[0].id)
        self.assertIsNotNone(self.db.get(EventRegistration, registration.id))

    def test_duplicate_registration_does_not_publish_event(self):
        register_for_event(self.events[0].id, self.user, self.db)
        settings.kafka_enabled = True
        events = []
        with patch(
            "app.messaging.producer.get_kafka_producer",
            return_value=FakeKafkaProducer(events),
        ) as get_producer:
            with self.assertRaises(HTTPException) as context:
                register_for_event(
                    self.events[0].id,
                    self.user,
                    self.db,
                    self.make_request(),
                )

        self.assertEqual(context.exception.status_code, 409)
        get_producer.assert_not_called()
        self.assertEqual(events, [])


if __name__ == "__main__":
    # run the event tests directly without requiring a separate test runner
    import unittest

    unittest.main()
