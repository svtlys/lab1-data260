"""focused tests for the Kafka event envelope foundation."""

from datetime import datetime, timezone
from uuid import UUID
from unittest import TestCase

from pydantic import ValidationError

from app.messaging.envelope import (
    APPLICATION_CREATED,
    APPLICATION_STATUS_CHANGED,
    APPLICATION_UPDATED,
    EVENT_REGISTRATION_CREATED,
    EVENT_TYPES,
    JOB_CREATED,
    MEMORY_CONSOLIDATE,
    Actor,
    EventEnvelope,
    create_envelope,
    kafka_key,
)


class KafkaEnvelopeTests(TestCase):
    def test_create_envelope_generates_ids_and_utc_timestamp(self):
        envelope = create_envelope(
            APPLICATION_CREATED,
            {"application_id": 16, "job_id": 4},
            Actor(user_id=7, role="student"),
        )
        data = envelope.to_dict()

        UUID(data["event_id"])
        UUID(data["trace_id"])
        self.assertEqual(data["event_type"], APPLICATION_CREATED)
        self.assertEqual(data["actor"], {"user_id": 7, "role": "student"})
        self.assertEqual(data["payload"]["application_id"], 16)
        self.assertTrue(data["occurred_at"].endswith("Z"))

    def test_serialization_normalizes_non_utc_input(self):
        envelope = create_envelope(
            JOB_CREATED,
            {"job_id": 16},
            {"user_id": None, "role": None},
            occurred_at=datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(envelope.to_dict()["occurred_at"], "2026-11-11T12:00:00Z")
        self.assertEqual(envelope.to_json().count("occurred_at"), 1)

    def test_all_agreed_event_types_are_available(self):
        self.assertEqual(
            EVENT_TYPES,
            {
                APPLICATION_CREATED,
                APPLICATION_UPDATED,
                APPLICATION_STATUS_CHANGED,
                EVENT_REGISTRATION_CREATED,
                JOB_CREATED,
                MEMORY_CONSOLIDATE,
            },
        )

    def test_missing_required_fields_are_rejected(self):
        with self.assertRaises(ValidationError):
            EventEnvelope.model_validate({})

    def test_invalid_uuid_values_are_rejected(self):
        with self.assertRaises(ValidationError):
            create_envelope(
                APPLICATION_UPDATED,
                {"application_id": 1},
                {"user_id": 1, "role": "student"},
                trace_id="not-a-uuid",
            )

        with self.assertRaises(ValidationError):
            create_envelope(
                APPLICATION_UPDATED,
                {"application_id": 1},
                {"user_id": 1, "role": "student"},
                event_id="not-a-uuid",
            )

    def test_invalid_event_types_are_rejected(self):
        with self.assertRaises(ValidationError):
            create_envelope(
                "application.deleted",
                {"application_id": 1},
                {"user_id": 1, "role": "student"},
            )

    def test_naive_timestamps_are_rejected(self):
        with self.assertRaises(ValidationError):
            create_envelope(
                EVENT_REGISTRATION_CREATED,
                {"event_id": 1},
                {"user_id": 1, "role": "student"},
                occurred_at=datetime(2026, 11, 11),
            )

    def test_payload_must_be_a_json_object(self):
        with self.assertRaises(ValidationError):
            create_envelope(
                MEMORY_CONSOLIDATE,
                {"value": object()},
                {"user_id": None, "role": "system"},
            )

    def test_actor_allows_null_identity_fields(self):
        envelope = create_envelope(
            MEMORY_CONSOLIDATE,
            {"student_id": 16},
            {"user_id": None, "role": None},
        )

        self.assertEqual(envelope.to_dict()["actor"], {"user_id": None, "role": None})

    def test_kafka_key_preserves_numeric_id_as_string(self):
        self.assertEqual(kafka_key(16), "16")

        with self.assertRaises(TypeError):
            kafka_key("16")

        with self.assertRaises(TypeError):
            kafka_key(True)


if __name__ == "__main__":
    import unittest

    unittest.main()
