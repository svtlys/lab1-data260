"""
test student job browsing and company job posting routes.
"""

import json
from datetime import date, datetime, timezone
import re
from unittest import TestCase
from unittest.mock import patch

from fastapi import HTTPException
from pydantic import ValidationError
from starlette.requests import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import require_company, require_student
from app.api.routes.jobs import create_job, get_job_details, get_my_jobs, job_response, search_jobs
from app.core.config import settings
from app.core.database import Base
from app.models.company_profile import CompanyProfile
from app.models.job import Job
from app.models.user import User, UserRole
from app.schemas.job import EMPLOYMENT_TYPE_VALUES, JobCreateRequest, JobResponse


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
            if isinstance(expected, dict) and "$in" in expected:
                if actual not in expected["$in"]:
                    return False
            elif isinstance(expected, dict) and "$regex" in expected:
                flags = re.IGNORECASE if "i" in expected.get("$options", "") else 0
                if re.search(expected["$regex"], str(actual or ""), flags) is None:
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

    def count_documents(self, query):
        return sum(self.matches(document, query) for document in self.documents)


class FakeMongoDatabase:
    def __init__(self, documents):
        self.collections = {
            "jobs": FakeMongoCollection(documents),
            "applications": FakeMongoCollection([]),
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
        self.original_kafka_enabled = settings.kafka_enabled
        settings.kafka_enabled = False
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
                "path": "/api/companies/me/jobs",
                "headers": headers,
            }
        )

    def migrated_job_documents(self):
        return [
            {
                "id": job.id,
                "company_id": job.company_id,
                "title": job.title,
                "description": job.description,
                "company_name": job.company_name,
                "location": job.location,
                "city": job.city,
                "employment_type": job.employment_type.lower(),
                "is_remote": job.is_remote,
                "salary_min": job.salary_min,
                "salary_max": job.salary_max,
                "required_skills": job.required_skills,
                "posted_at": job.posted_at,
                "deadline": (
                    datetime.combine(job.deadline, datetime.min.time())
                    if job.deadline
                    else None
                ),
            }
            for job in self.db.query(Job).all()
        ]

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

    def test_job_creation_kafka_disabled_skips_publish_and_preserves_response(self):
        events = []
        with patch(
            "app.messaging.producer.get_kafka_producer",
            return_value=FakeKafkaProducer(events),
        ) as get_producer:
            created = create_job(
                JobCreateRequest(
                    title="Analytics Intern",
                    description="Build dashboards for local teams.",
                    employment_type="Internship",
                    city="Sunnyvale",
                ),
                self.company_user,
                self.db,
                self.make_request(),
            )

        get_producer.assert_not_called()
        self.assertEqual(created["company_id"], self.company_profile.id)
        self.assertEqual(created["title"], "Analytics Intern")
        self.assertEqual(events, [])

    def test_job_created_event_metadata_and_payload_are_correct(self):
        settings.kafka_enabled = True
        events = []
        trace_id = "22222222-2222-4222-8222-222222222222"
        with patch(
            "app.messaging.producer.get_kafka_producer",
            return_value=FakeKafkaProducer(events),
        ):
            created = create_job(
                JobCreateRequest(
                    title="Analytics Intern",
                    description="Build dashboards for local teams.",
                    employment_type="Internship",
                    city="Sunnyvale",
                    is_remote=True,
                ),
                self.company_user,
                self.db,
                self.make_request(trace_id),
            )

        self.assertEqual(len(events), 1)
        topic, key, value = events[0]
        message = json.loads(value)
        self.assertEqual(topic, "p16.job.created")
        self.assertEqual(key, str(created["id"]))
        self.assertEqual(message["event_type"], "job.created")
        self.assertEqual(message["trace_id"], trace_id)
        self.assertEqual(
            message["actor"],
            {"user_id": self.company_user.id, "role": "company"},
        )
        self.assertEqual(
            message["payload"],
            {
                "job_id": created["id"],
                "company_id": self.company_profile.id,
                "title": "Analytics Intern",
                "city": "Sunnyvale",
                "employment_type": "Internship",
                "is_remote": True,
                "posted_at": created["posted_at"].replace(
                    tzinfo=timezone.utc
                ).isoformat().replace("+00:00", "Z"),
            },
        )

    def test_job_creation_commits_before_publish(self):
        settings.kafka_enabled = True
        order = []
        original_commit = self.db.commit

        def commit_then_record():
            original_commit()
            order.append("commit")

        with patch.object(self.db, "commit", side_effect=commit_then_record), patch(
            "app.messaging.producer.get_kafka_producer",
            return_value=FakeKafkaProducer(order),
        ):
            created = create_job(
                JobCreateRequest(
                    title="Analytics Intern",
                    description="Build dashboards for local teams.",
                    employment_type="Internship",
                    city="Sunnyvale",
                ),
                self.company_user,
                self.db,
                self.make_request(),
            )

        self.assertIsNotNone(self.db.get(Job, created["id"]))
        self.assertEqual(order[0], "commit")
        self.assertEqual(order[1][0], "p16.job.created")
        self.assertEqual(order[1][1], str(created["id"]))

    def test_job_creation_publish_failure_preserves_commit_and_response(self):
        settings.kafka_enabled = True
        with patch(
            "app.messaging.producer.get_kafka_producer",
            return_value=FailingKafkaProducer(),
        ):
            created = create_job(
                JobCreateRequest(
                    title="Analytics Intern",
                    description="Build dashboards for local teams.",
                    employment_type="Internship",
                    city="Sunnyvale",
                ),
                self.company_user,
                self.db,
                self.make_request(),
            )

        self.assertIsNotNone(self.db.get(Job, created["id"]))
        self.assertEqual(created["company_id"], self.company_profile.id)

    def test_invalid_job_request_does_not_publish_event(self):
        events = []
        with patch(
            "app.messaging.producer.get_kafka_producer",
            return_value=FakeKafkaProducer(events),
        ) as get_producer:
            with self.assertRaises(ValidationError):
                JobCreateRequest(
                    title="x",
                    description="too short",
                    employment_type="Internship",
                    city="Sunnyvale",
                )

        get_producer.assert_not_called()
        self.assertEqual(events, [])

    def test_authorization_failure_does_not_publish_event(self):
        events = []
        with patch(
            "app.messaging.producer.get_kafka_producer",
            return_value=FakeKafkaProducer(events),
        ) as get_producer:
            with self.assertRaises(HTTPException) as context:
                require_company(self.student_user)

        self.assertEqual(context.exception.status_code, 403)
        get_producer.assert_not_called()
        self.assertEqual(events, [])

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

    def test_job_response_normalizes_legacy_lowercase_employment_types(self):
        legacy_types = {
            "internship": "Internship",
            "full-time": "Full-time",
            "part-time": "Part-time",
            "on-campus": "On-campus",
        }
        jobs = []
        for index, legacy_type in enumerate(legacy_types, start=1):
            jobs.append(
                Job(
                    company_id=self.company_profile.id,
                    title=f"Legacy job {index}",
                    description="A legacy job fixture for response compatibility.",
                    company_name="First Company",
                    location="Sunnyvale, CA",
                    city="Sunnyvale",
                    employment_type=legacy_type,
                    is_remote=False,
                    posted_at=datetime(2026, 10, 10 + index),
                )
            )
        self.db.add_all(jobs)
        self.db.commit()

        for job, expected_type in zip(jobs, legacy_types.values()):
            payload = job_response(job, self.db)
            self.assertEqual(payload["employment_type"], expected_type)
            self.assertEqual(self.db.get(Job, job.id).employment_type, job.employment_type)

    def test_job_response_preserves_unknown_employment_type_for_validation(self):
        job = Job(
            company_id=self.company_profile.id,
            title="Unknown type job",
            description="An unknown employment type must remain invalid.",
            company_name="First Company",
            location="Sunnyvale, CA",
            city="Sunnyvale",
            employment_type="contract",
            is_remote=False,
            posted_at=datetime(2026, 10, 20),
        )
        self.db.add(job)
        self.db.commit()

        payload = job_response(job, self.db)
        self.assertEqual(payload["employment_type"], "contract")
        with self.assertRaises(ValidationError):
            JobResponse.model_validate(payload)

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

    def test_mongo_search_matches_mysql_response_for_migrated_jobs(self):
        mysql_jobs = search_jobs(
            search="Python",
            city="Sunnyvale",
            employment_type="Internship",
            is_remote=False,
            current_user=self.student_user,
            db=self.db,
        )
        mongo_database = FakeMongoDatabase(self.migrated_job_documents())

        with patch(
            "app.api.routes.jobs.get_mongo_database",
            return_value=mongo_database,
        ):
            mongo_jobs = search_jobs(
                search="Python",
                city="Sunnyvale",
                employment_type="Internship",
                is_remote=False,
                current_user=self.student_user,
                db=self.db,
            )

        self.assertEqual(mongo_jobs, mysql_jobs)
        self.assertNotIn("_id", mongo_jobs[0])

    def test_mongo_job_details_match_mysql_and_fallback_preserves_results(self):
        mysql_details = get_job_details(1, self.student_user, self.db)
        mongo_database = FakeMongoDatabase(self.migrated_job_documents())

        with patch(
            "app.api.routes.jobs.get_mongo_database",
            return_value=mongo_database,
        ):
            mongo_details = get_job_details(1, self.student_user, self.db)

        self.assertEqual(mongo_details, mysql_details)
        self.assertNotIn("_id", mongo_details)

        with patch(
            "app.api.routes.jobs.get_mongo_database",
            side_effect=RuntimeError("mongo unavailable"),
        ):
            fallback = search_jobs(
                search="Python",
                city=None,
                employment_type=None,
                is_remote=None,
                current_user=self.student_user,
                db=self.db,
            )

        expected = search_jobs(
            search="Python",
            city=None,
            employment_type=None,
            is_remote=None,
            current_user=self.student_user,
            db=self.db,
        )
        self.assertEqual(fallback, expected)

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
