"""test the Kafka consumer reliability foundation with fakes only."""

from datetime import datetime, timezone
import json
from types import ModuleType
from unittest import TestCase
from unittest.mock import patch

from app.messaging.consumer import (
    KafkaConsumerConfig,
    create_consumer,
    process_record,
)
from app.messaging.envelope import APPLICATION_CREATED, create_envelope


class FakeProcessedCollection:
    def __init__(self, order=None):
        self.documents = {}
        self.order = order if order is not None else []

    def find_one(self, query):
        return self.documents.get(query["event_id"])

    def update_one(self, query, update, upsert=False):
        event_id = query["event_id"]
        if event_id not in self.documents and upsert:
            self.order.append("record")
            self.documents[event_id] = update["$setOnInsert"].copy()


class FakeDatabase:
    def __init__(self, order=None):
        self.processed_events = FakeProcessedCollection(order)

    def __getitem__(self, collection):
        self.assert_collection(collection)
        return self.processed_events

    @staticmethod
    def assert_collection(collection):
        if collection != "processed_events":
            raise AssertionError(f"unexpected collection: {collection}")


class FakeRecord:
    def __init__(self, value):
        self.value = value


class FakeConsumer:
    def __init__(self, order=None):
        self.commits = 0
        self.order = order if order is not None else []

    def commit(self):
        self.commits += 1
        self.order.append("commit")


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
        raise RuntimeError("secret broker password")


class KafkaConsumerTests(TestCase):
    def setUp(self):
        self.event_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
        self.trace_id = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
        self.envelope = create_envelope(
            APPLICATION_CREATED,
            {"application_id": 17},
            {"user_id": 9, "role": "student"},
            event_id=self.event_id,
            trace_id=self.trace_id,
            occurred_at=datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc),
        )
        self.record = FakeRecord(self.envelope.to_json())

    def test_consumer_disables_auto_commit_and_sets_group(self):
        captured = {}

        class FakeKafkaConsumer:
            def __init__(self, *topics, **kwargs):
                captured["topics"] = topics
                captured["kwargs"] = kwargs

        kafka_module = ModuleType("kafka")
        kafka_module.KafkaConsumer = FakeKafkaConsumer
        config = KafkaConsumerConfig(group_id="p16-application-workers")
        with patch.dict("sys.modules", {"kafka": kafka_module}):
            create_consumer(["p16.application.created"], config)

        self.assertEqual(captured["topics"], ("p16.application.created",))
        self.assertEqual(captured["kwargs"]["group_id"], "p16-application-workers")
        self.assertFalse(captured["kwargs"]["enable_auto_commit"])

    def test_duplicate_event_is_skipped_and_handler_runs_once_total(self):
        database = FakeDatabase()
        consumer = FakeConsumer()
        producer = FakeProducer()
        calls = []

        first = process_record(
            self.record,
            database=database,
            handler=lambda event: calls.append(event.event_id),
            consumer=consumer,
            dlq_producer=producer,
        )
        second = process_record(
            self.record,
            database=database,
            handler=lambda event: calls.append(event.event_id),
            consumer=consumer,
            dlq_producer=producer,
        )

        self.assertEqual(first.status, "processed")
        self.assertEqual(second.status, "duplicate_skipped")
        self.assertEqual(calls, [self.envelope.event_id])
        self.assertEqual(consumer.commits, 2)

    def test_handler_runs_before_processed_event_is_recorded_and_then_commits(self):
        order = []
        database = FakeDatabase(order)
        consumer = FakeConsumer(order)

        result = process_record(
            self.record,
            database=database,
            handler=lambda event: order.append("handler"),
            consumer=consumer,
            dlq_producer=FakeProducer(),
        )

        self.assertEqual(result.status, "processed")
        self.assertEqual(order, ["handler", "record", "commit"])

    def test_first_and_second_failures_retry_and_third_failure_goes_to_dlq(self):
        database = FakeDatabase()
        consumer = FakeConsumer()
        events = []
        producer = FakeProducer(events)
        calls = []

        def handler(event):
            calls.append(event.event_id)
            raise RuntimeError("password=do-not-log")

        result = process_record(
            self.record,
            database=database,
            handler=handler,
            consumer=consumer,
            dlq_producer=producer,
        )

        self.assertEqual(result.status, "dead_lettered")
        self.assertEqual(result.attempts, 3)
        self.assertEqual(len(calls), 3)
        self.assertEqual(consumer.commits, 1)
        self.assertEqual(events[0][0], "p16.dlq")
        self.assertEqual(events[0][1], self.event_id)
        dlq = json.loads(events[0][2])
        self.assertEqual(dlq["event_id"], self.event_id)
        self.assertEqual(dlq["trace_id"], self.trace_id)
        self.assertEqual(dlq["payload"]["original_envelope"]["event_id"], self.event_id)
        self.assertEqual(dlq["payload"]["failure"]["attempts"], 3)

    def test_successful_dlq_publish_is_followed_by_offset_commit(self):
        order = []
        database = FakeDatabase(order)
        consumer = FakeConsumer(order)

        result = process_record(
            self.record,
            database=database,
            handler=lambda event: (_ for _ in ()).throw(RuntimeError("failure")),
            consumer=consumer,
            dlq_producer=FakeProducer(),
        )

        self.assertEqual(result.status, "dead_lettered")
        self.assertEqual(order, ["commit"])

    def test_failed_dlq_publish_leaves_offset_uncommitted(self):
        database = FakeDatabase()
        consumer = FakeConsumer()

        result = process_record(
            self.record,
            database=database,
            handler=lambda event: (_ for _ in ()).throw(RuntimeError("failure")),
            consumer=consumer,
            dlq_producer=FailingProducer(),
        )

        self.assertEqual(result.status, "dlq_failed")
        self.assertFalse(result.offset_committed)
        self.assertEqual(consumer.commits, 0)

    def test_handler_success_commits_only_after_recording(self):
        order = []
        database = FakeDatabase(order)
        consumer = FakeConsumer(order)
        result = process_record(
            self.record,
            database=database,
            handler=lambda event: order.append("handler"),
            consumer=consumer,
            dlq_producer=FakeProducer(),
        )

        self.assertEqual(result.status, "processed")
        self.assertEqual(order[-1], "commit")
        self.assertEqual(order, ["handler", "record", "commit"])

    def test_sensitive_values_are_not_logged(self):
        database = FakeDatabase()
        consumer = FakeConsumer()

        with self.assertLogs("app.messaging.consumer", level="WARNING") as captured:
            process_record(
                self.record,
                database=database,
                handler=lambda event: (_ for _ in ()).throw(
                    RuntimeError("password=secret-token")
                ),
                consumer=consumer,
                dlq_producer=FailingProducer(),
            )

        output = "\n".join(captured.output)
        self.assertNotIn("secret-token", output)
        self.assertNotIn("password", output)


if __name__ == "__main__":
    import unittest

    unittest.main()
