"""
test job application ownership, status, duplicate, and PDF behavior.
"""

import asyncio
import json
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from fastapi import HTTPException, UploadFile
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from starlette.datastructures import Headers
from starlette.requests import Request

from app.api.routes.applications import (
    apply_to_job,
    get_job_applications,
    get_my_applications,
    get_application_resume,
    read_pdf_resume,
    update_application_status,
    update_application_status_legacy,
)
from app.core.database import Base
from app.core.config import settings
from app.models.application import Application
from app.models.company_profile import CompanyProfile
from app.models.job import Job
from app.models.student_profile import StudentProfile
from app.models.user import User, UserRole
from app.schemas.application import ApplicationStatusUpdateRequest


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

    def find(self, query):
        return FakeMongoCursor(
            [
                document
                for document in self.documents
                if all(document.get(field) == value for field, value in query.items())
            ]
        )

    def find_one(self, query):
        return next(iter(self.find(query)), None)


class FakeMongoDatabase:
    def __init__(self, collections):
        self.collections = {
            name: FakeMongoCollection(documents)
            for name, documents in collections.items()
        }

    def __getitem__(self, collection):
        return self.collections[collection]


class FakeFuture:
    def get(self, timeout):
        return None


class FakeProducer:
    def __init__(self, events=None):
        self.events = events if events is not None else []

    def send(self, topic, key, value):
        self.events.append((topic, key, value))
        return FakeFuture()


class FailingProducer:
    def send(self, topic, key, value):
        raise RuntimeError("broker failure details")


class FailingTopicProducer:
    def __init__(self, failing_topic):
        self.failing_topic = failing_topic
        self.events = []

    def send(self, topic, key, value):
        if topic == self.failing_topic:
            raise RuntimeError("broker failure details")
        self.events.append((topic, key, value))
        return FakeFuture()


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
        self.original_kafka_enabled = settings.kafka_enabled
        settings.kafka_enabled = False

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
        settings.kafka_enabled = self.original_kafka_enabled

    def migrated_application_database(self, include_resume=False):
        applications = []
        for application in self.db.query(Application).all():
            applications.append(
                {
                    "id": application.id,
                    "job_id": application.job_id,
                    "student_id": application.student_id,
                    "status": application.status,
                    "applied_at": application.applied_at,
                    "resume_filename": application.resume_filename,
                }
            )
        jobs = [
            {
                "id": self.job.id,
                "company_id": self.job.company_id,
                "title": self.job.title,
                "company_name": self.job.company_name,
            }
        ]
        students = [
            {
                "id": self.student_profile.id,
                "user_id": self.student_profile.user_id,
                "full_name": self.student_profile.full_name,
                "college_name": self.student_profile.college_name,
                "major": self.student_profile.major,
            }
        ]
        companies = [
            {"id": self.company_profile.id, "user_id": self.company_profile.user_id}
        ]
        resumes = []
        if include_resume:
            application = self.db.query(Application).one()
            resumes.append(
                {
                    "id": application.id,
                    "application_id": application.id,
                    "filename": application.resume_filename,
                    "content": b"%PDF-1.7 test resume",
                }
            )
        return FakeMongoDatabase(
            {
                "applications": applications,
                "jobs": jobs,
                "student_profiles": students,
                "company_profiles": companies,
                "resumes": resumes,
            }
        )

    def make_pdf_upload(self, filename="resume.pdf"):
        return UploadFile(
            file=BytesIO(b"%PDF-1.7 test resume"),
            filename=filename,
            headers=Headers({"content-type": "application/pdf"}),
        )

    @staticmethod
    def make_request(trace_id=None):
        headers = []
        if trace_id:
            headers.append((b"x-trace-id", trace_id.encode()))
        return Request(
            {
                "type": "http",
                "method": "POST",
                "scheme": "http",
                "server": ("127.0.0.1", 9160),
                "path": "/api/jobs/1/applications",
                "headers": headers,
            }
        )

    def test_student_can_apply_with_pdf_and_view_own_application(self):
        application_data = asyncio.run(
            apply_to_job(
                self.job.id,
                request=self.make_request(),
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

    def test_mongo_student_applications_match_mysql_response(self):
        asyncio.run(
            apply_to_job(
                self.job.id,
                request=self.make_request(),
                resume=None,
                current_user=self.student_user,
                db=self.db,
            )
        )
        mysql_rows = get_my_applications(self.student_user, self.db)
        database = self.migrated_application_database()

        with patch(
            "app.api.routes.applications.get_mongo_database",
            return_value=database,
        ):
            mongo_rows = get_my_applications(self.student_user, self.db)

        self.assertEqual(mongo_rows, mysql_rows)
        self.assertTrue(all("_id" not in row for row in mongo_rows))

    def test_mongo_company_applications_preserve_ownership_and_shape(self):
        asyncio.run(
            apply_to_job(
                self.job.id,
                request=self.make_request(),
                resume=None,
                current_user=self.student_user,
                db=self.db,
            )
        )
        mysql_rows = get_job_applications(self.job.id, self.company_user, self.db)
        database = self.migrated_application_database()

        with patch(
            "app.api.routes.applications.get_mongo_database",
            return_value=database,
        ):
            mongo_rows = get_job_applications(self.job.id, self.company_user, self.db)
            with self.assertRaises(HTTPException) as context:
                get_job_applications(self.job.id, self.other_company_user, self.db)

        self.assertEqual(mongo_rows, mysql_rows)
        self.assertEqual(context.exception.status_code, 404)

    def test_mongo_resume_read_preserves_filename_and_content(self):
        application_data = asyncio.run(
            apply_to_job(
                self.job.id,
                request=self.make_request(),
                resume=self.make_pdf_upload("candidate.pdf"),
                current_user=self.student_user,
                db=self.db,
            )
        )
        stored_path = self.db.get(Application, application_data["id"]).resume_path
        self.created_paths.append(stored_path)
        database = self.migrated_application_database(include_resume=True)

        with patch(
            "app.api.routes.applications.get_mongo_database",
            return_value=database,
        ):
            response = get_application_resume(
                application_data["id"],
                self.company_user,
                self.db,
            )

        self.assertEqual(response.body, b"%PDF-1.7 test resume")
        self.assertEqual(response.media_type, "application/pdf")
        self.assertIn("candidate.pdf", response.headers["content-disposition"])

    def test_application_reads_fall_back_to_mysql_when_mongo_is_unavailable(self):
        asyncio.run(
            apply_to_job(
                self.job.id,
                request=self.make_request(),
                resume=None,
                current_user=self.student_user,
                db=self.db,
            )
        )
        with patch(
            "app.api.routes.applications.get_mongo_database",
            side_effect=RuntimeError("mongo unavailable"),
        ):
            rows = get_my_applications(self.student_user, self.db)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], "Pending")

    def test_duplicate_application_is_rejected(self):
        asyncio.run(
            apply_to_job(
                self.job.id,
                request=self.make_request(),
                resume=None,
                current_user=self.student_user,
                db=self.db,
            )
        )

        with self.assertRaises(HTTPException) as context:
            asyncio.run(
                apply_to_job(
                    self.job.id,
                    request=self.make_request(),
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
                request=self.make_request(),
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

    def create_pending_application(self):
        asyncio.run(
            apply_to_job(
                self.job.id,
                request=self.make_request(),
                resume=None,
                current_user=self.student_user,
                db=self.db,
            )
        )
        return self.db.query(Application).one()

    def test_status_change_kafka_disabled_preserves_response_and_skips_publish(self):
        application = self.create_pending_application()
        fake_producer = FakeProducer()

        with patch(
            "app.messaging.producer.get_kafka_producer",
            return_value=fake_producer,
        ) as get_producer:
            response = update_application_status(
                application.id,
                ApplicationStatusUpdateRequest(status="Reviewed"),
                self.company_user,
                self.db,
            )

        get_producer.assert_not_called()
        self.assertEqual(response["status"], "Reviewed")
        self.assertEqual(fake_producer.events, [])

    def test_status_change_event_metadata_and_previous_status_are_correct(self):
        application = self.create_pending_application()
        settings.kafka_enabled = True
        fake_producer = FakeProducer()
        trace_id = "12345678-1234-4234-8234-123456789012"

        with patch(
            "app.messaging.producer.get_kafka_producer",
            return_value=fake_producer,
        ):
            response = update_application_status(
                application.id,
                ApplicationStatusUpdateRequest(status="Reviewed"),
                self.company_user,
                self.db,
                self.make_request(trace_id),
            )

        self.assertEqual(len(fake_producer.events), 2)
        events = {
            json.loads(serialized)["event_type"]: (topic, key, json.loads(serialized))
            for topic, key, serialized in fake_producer.events
        }
        self.assertEqual(response["status"], "Reviewed")
        self.assertEqual(
            set(events),
            {"application.updated", "application.status_changed"},
        )
        updated_event = events["application.updated"][2]
        status_event = events["application.status_changed"][2]
        self.assertEqual(
            events["application.updated"][:2],
            ("p16.application.updated", str(application.id)),
        )
        self.assertEqual(
            events["application.status_changed"][:2],
            ("p16.application.status_changed", str(application.id)),
        )
        self.assertEqual(updated_event["trace_id"], trace_id)
        self.assertEqual(status_event["trace_id"], trace_id)
        self.assertEqual(
            updated_event["actor"],
            {"user_id": self.company_user.id, "role": "company"},
        )
        self.assertEqual(status_event["actor"], updated_event["actor"])
        expected_payload = {
            "application_id": application.id,
            "job_id": self.job.id,
            "student_id": self.student_profile.id,
            "previous_status": "Pending",
            "new_status": "Reviewed",
            "updated_at": updated_event["payload"]["updated_at"],
        }
        self.assertEqual(updated_event["payload"], expected_payload)
        self.assertEqual(status_event["payload"], expected_payload)
        self.assertIsNotNone(
            datetime.fromisoformat(
                expected_payload["updated_at"].replace("Z", "+00:00")
            ).tzinfo
        )

    def test_status_change_commits_before_publish(self):
        application = self.create_pending_application()
        settings.kafka_enabled = True
        order = []
        fake_producer = FakeProducer(order)
        original_commit = self.db.commit

        def commit_then_record():
            original_commit()
            order.append("commit")

        with (
            patch.object(self.db, "commit", side_effect=commit_then_record),
            patch(
                "app.messaging.producer.get_kafka_producer",
                return_value=fake_producer,
            ),
        ):
            update_application_status(
                application.id,
                ApplicationStatusUpdateRequest(status="Reviewed"),
                self.company_user,
                self.db,
            )

        self.assertEqual(order[0], "commit")
        self.assertEqual(order[1][0], "p16.application.updated")
        self.assertEqual(order[2][0], "p16.application.status_changed")

    def test_patch_and_put_aliases_each_publish_once(self):
        application = self.create_pending_application()
        settings.kafka_enabled = True
        fake_producer = FakeProducer()

        with patch(
            "app.messaging.producer.get_kafka_producer",
            return_value=fake_producer,
        ):
            update_application_status(
                application.id,
                ApplicationStatusUpdateRequest(status="Reviewed"),
                self.company_user,
                self.db,
                self.make_request(),
            )
            update_application_status_legacy(
                application.id,
                ApplicationStatusUpdateRequest(status="Declined"),
                self.company_user,
                self.db,
                self.make_request(),
            )

        self.assertEqual(len(fake_producer.events), 4)
        first_pair = [json.loads(event[2])["event_type"] for event in fake_producer.events[:2]]
        second_pair = [json.loads(event[2])["event_type"] for event in fake_producer.events[2:]]
        self.assertEqual(
            first_pair,
            ["application.updated", "application.status_changed"],
        )
        self.assertEqual(
            second_pair,
            ["application.updated", "application.status_changed"],
        )
        self.assertEqual(
            json.loads(fake_producer.events[0][2])["payload"]["previous_status"],
            "Pending",
        )
        self.assertEqual(
            json.loads(fake_producer.events[3][2])["payload"]["previous_status"],
            "Reviewed",
        )

    def test_status_publish_failure_preserves_committed_update_and_response(self):
        application = self.create_pending_application()
        settings.kafka_enabled = True

        with patch(
            "app.messaging.producer.get_kafka_producer",
            return_value=FailingProducer(),
        ):
            response = update_application_status(
                application.id,
                ApplicationStatusUpdateRequest(status="Reviewed"),
                self.company_user,
                self.db,
            )

        self.assertEqual(response["status"], "Reviewed")
        self.assertEqual(self.db.get(Application, application.id).status, "Reviewed")

    def test_one_status_event_failure_preserves_update_and_attempts_other_event(self):
        application = self.create_pending_application()
        settings.kafka_enabled = True
        producer = FailingTopicProducer("p16.application.updated")

        with patch(
            "app.messaging.producer.get_kafka_producer",
            return_value=producer,
        ):
            response = update_application_status(
                application.id,
                ApplicationStatusUpdateRequest(status="Reviewed"),
                self.company_user,
                self.db,
            )

        self.assertEqual(response["status"], "Reviewed")
        self.assertEqual(self.db.get(Application, application.id).status, "Reviewed")
        self.assertEqual(len(producer.events), 1)
        self.assertEqual(producer.events[0][0], "p16.application.status_changed")

    def test_invalid_status_is_rejected_before_route_update(self):
        with self.assertRaises(ValidationError):
            ApplicationStatusUpdateRequest(status="Invalid")

    def test_non_pdf_upload_is_rejected(self):
        with self.assertRaises(HTTPException) as context:
            asyncio.run(read_pdf_resume(self.make_pdf_upload("resume.txt")))

        self.assertEqual(context.exception.status_code, 415)

    def test_kafka_disabled_skips_publish_and_preserves_response(self):
        fake_producer = FakeProducer()

        with patch(
            "app.messaging.producer.get_kafka_producer",
            return_value=fake_producer,
        ) as get_producer:
            response = asyncio.run(
                apply_to_job(
                    self.job.id,
                    request=self.make_request(),
                    resume=None,
                    current_user=self.student_user,
                    db=self.db,
                )
            )

        get_producer.assert_not_called()
        self.assertEqual(response["status"], "Pending")
        self.assertEqual(response["job_id"], self.job.id)
        self.assertEqual(fake_producer.events, [])

    def test_successful_application_commits_before_publishing_event(self):
        settings.kafka_enabled = True
        order = []
        fake_producer = FakeProducer(order)
        original_commit = self.db.commit

        def commit_then_record():
            original_commit()
            order.append("commit")

        with (
            patch.object(self.db, "commit", side_effect=commit_then_record),
            patch(
                "app.messaging.producer.get_kafka_producer",
                return_value=fake_producer,
            ),
        ):
            response = asyncio.run(
                apply_to_job(
                    self.job.id,
                    request=self.make_request(
                        "12345678-1234-4234-8234-123456789012"
                    ),
                    resume=None,
                    current_user=self.student_user,
                    db=self.db,
                )
            )

        self.assertEqual(response["status"], "Pending")
        self.assertEqual(order[0], "commit")
        self.assertEqual(order[1][0], "p16.application.created")
        self.assertEqual(order[1][1], "1")

    def test_event_metadata_topic_key_payload_and_trace_are_correct(self):
        settings.kafka_enabled = True
        fake_producer = FakeProducer()
        trace_id = "12345678-1234-4234-8234-123456789012"

        with patch(
            "app.messaging.producer.get_kafka_producer",
            return_value=fake_producer,
        ):
            response = asyncio.run(
                apply_to_job(
                    self.job.id,
                    request=self.make_request(trace_id),
                    resume=self.make_pdf_upload("candidate.pdf"),
                    current_user=self.student_user,
                    db=self.db,
                )
            )
        stored_path = self.db.get(Application, response["id"]).resume_path
        self.created_paths.append(stored_path)

        topic, key, serialized = fake_producer.events[0]
        event = json.loads(serialized)
        self.assertEqual(topic, "p16.application.created")
        self.assertEqual(key, str(response["id"]))
        self.assertEqual(event["event_type"], "application.created")
        self.assertEqual(event["trace_id"], trace_id)
        self.assertEqual(
            event["actor"],
            {"user_id": self.student_user.id, "role": "student"},
        )
        self.assertEqual(
            event["payload"],
            {
                "application_id": response["id"],
                "job_id": self.job.id,
                "student_id": self.student_profile.id,
                "status": "Pending",
                "resume_filename": "candidate.pdf",
            },
        )

    def test_publish_failure_preserves_committed_api_response(self):
        settings.kafka_enabled = True

        with patch(
            "app.messaging.producer.get_kafka_producer",
            return_value=FailingProducer(),
        ):
            response = asyncio.run(
                apply_to_job(
                    self.job.id,
                    request=self.make_request(),
                    resume=None,
                    current_user=self.student_user,
                    db=self.db,
                )
            )

        self.assertEqual(response["status"], "Pending")
        self.assertEqual(response["job_id"], self.job.id)
        self.assertIsNotNone(self.db.query(Application).one())


if __name__ == "__main__":
    import unittest

    unittest.main()
