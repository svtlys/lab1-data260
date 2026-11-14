"""focused tests for the optional Kafka producer foundation."""

import json
from unittest import TestCase
from unittest.mock import Mock, patch

from app.core.config import Settings
from app.core.kafka import create_kafka_producer, get_kafka_producer
from app.messaging.envelope import APPLICATION_CREATED, create_envelope
from app.messaging.producer import KafkaPublishError, publish_event, topic_name


class KafkaProducerTests(TestCase):
    def make_settings(self, enabled=False):
        return Settings(
            _env_file=None,
            db_host="mysql",
            db_port=3306,
            db_user="user",
            db_password="password",
            db_name="p16_handshake",
            jwt_secret_key="unit-test-jwt-secret-only",
            kafka_enabled=enabled,
            kafka_bootstrap_servers="p16-kafka:9092",
            kafka_topic_prefix="p16",
            kafka_request_timeout_ms=5000,
            kafka_delivery_timeout_ms=10000,
            kafka_publish_timeout_seconds=1.0,
        )

    def make_envelope(self):
        return create_envelope(
            APPLICATION_CREATED,
            {"application_id": 16, "job_id": 4},
            {"user_id": 7, "role": "student"},
        )

    def test_topic_name_uses_p16_prefix(self):
        config = self.make_settings()

        self.assertEqual(topic_name("application.created", config), "p16.application.created")
        self.assertEqual(topic_name("p16.application.created", config), "p16.application.created")

    def test_disabled_publish_returns_safe_result_without_creating_producer(self):
        config = self.make_settings(enabled=False)

        with patch(
            "app.messaging.producer.get_kafka_producer",
            return_value=None,
        ) as get_producer:
            result = publish_event(self.make_envelope(), "application.created", 16, config=config)

        self.assertEqual(
            result,
            {
                "status": "disabled",
                "published": False,
                "topic": "p16.application.created",
            },
        )
        get_producer.assert_called_once_with(config)

    def test_enabled_publish_serializes_envelope_and_string_key(self):
        config = self.make_settings(enabled=True)
        future = Mock()
        producer = Mock()
        producer.send.return_value = future

        with patch("app.messaging.producer.get_kafka_producer", return_value=producer):
            result = publish_event(
                self.make_envelope(),
                "application.created",
                16,
                config=config,
            )

        self.assertEqual(result["status"], "published")
        self.assertEqual(result["topic"], "p16.application.created")
        self.assertEqual(result["key"], "16")
        producer.send.assert_called_once()
        topic, = producer.send.call_args.args
        kwargs = producer.send.call_args.kwargs
        self.assertEqual(topic, "p16.application.created")
        self.assertEqual(kwargs["key"], "16")
        serialized = json.loads(kwargs["value"])
        self.assertEqual(serialized["payload"]["application_id"], 16)
        future.get.assert_called_once_with(timeout=1.0)

    def test_publish_failure_is_sanitized(self):
        config = self.make_settings(enabled=True)
        producer = Mock()
        producer.send.side_effect = RuntimeError(
            "broker password and connection details must not leak"
        )

        with patch("app.messaging.producer.get_kafka_producer", return_value=producer):
            with self.assertRaisesRegex(KafkaPublishError, "^kafka publish failed$") as context:
                publish_event(self.make_envelope(), "application.created", 16, config=config)

        self.assertNotIn("password", str(context.exception))
        self.assertNotIn("connection", str(context.exception))

    def test_core_producer_is_disabled_without_connecting(self):
        config = self.make_settings(enabled=False)

        with patch("app.core.kafka.create_kafka_producer") as create:
            self.assertIsNone(get_kafka_producer(config))
            create.assert_not_called()

    def test_core_producer_omits_unsupported_delivery_timeout(self):
        config = self.make_settings(enabled=True)

        with patch("kafka.KafkaProducer") as producer_class:
            create_kafka_producer(config)

        kwargs = producer_class.call_args.kwargs
        self.assertEqual(kwargs["bootstrap_servers"], ["p16-kafka:9092"])
        self.assertEqual(kwargs["request_timeout_ms"], 5000)
        self.assertNotIn("delivery_timeout_ms", kwargs)


if __name__ == "__main__":
    import unittest

    unittest.main()
