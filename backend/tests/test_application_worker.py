"""test the application worker with fake Kafka and Mongo objects."""

from datetime import datetime, timezone
import json
from unittest import TestCase

from app.messaging.envelope import (
    APPLICATION_CREATED,
    APPLICATION_UPDATED,
    MEMORY_CONSOLIDATE,
    create_envelope,
)
from app.workers.application_worker import (
    APPLICATION_TOPICS,
    APPLICATION_WORKER_GROUP,
    ApplicationWorker,
    handle_application_event,
)


class FakeCollection:
    def __init__(self, order=None, fail=False):
        self.documents = {}
        self.order = order if order is not None else []
        self.fail = fail
        self.calls = 0

    def find_one(self, query):
        return self.documents.get(query.get("event_id"))

    def update_one(self, query, update, upsert=False):
        self.calls += 1
        if self.fail:
            raise RuntimeError("password=do-not-log")
        key = query.get("_id") or query.get("event_id")
        if key not in self.documents and upsert:
            self.order.append("activity" if "_id" in query else "processed")
            self.documents[key] = next(iter(update.values())).copy()


class FakeDatabase:
    def __init__(self, order=None, fail_activity=False):
        self.collections = {
            "activity_logs": FakeCollection(order, fail=fail_activity),
            "processed_events": FakeCollection(order),
        }

    def __getitem__(self, collection):
        return self.collections[collection]


class FakeRecord:
    def __init__(self, envelope):
        self.value = envelope.to_json()


class FakeConsumer:
    def __init__(self, order=None):
        self.order = order if order is not None else []
        self.commits = 0

    def commit(self):
        self.commits += 1
        self.order.append("commit")


class FakeFuture:
    def get(self, timeout):
        return None


class FakeProducer:
    def __init__(self):
        self.events = []

    def send(self, topic, key, value):
        self.events.append((topic, key, value))
        return FakeFuture()


class ApplicationWorkerTests(TestCase):
    def setUp(self):
        self.event_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
        self.trace_id = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"

    def make_envelope(self, event_type=APPLICATION_CREATED, event_id=None):
        return create_envelope(
            event_type,
            {
                "application_id": 17,
                "job_id": 8,
                "student_id": 9,
                "status": "Pending",
                "previous_status": "Pending",
                "new_status": "Reviewed",
            },
            {"user_id": 9, "role": "company"},
            event_id=event_id or self.event_id,
            trace_id=self.trace_id,
            occurred_at=datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc),
        )

    def test_worker_uses_distinct_group_and_topics(self):
        captured = {}

        def factory(topics, config):
            captured["topics"] = topics
            captured["config"] = config
            return FakeConsumer()

        worker = ApplicationWorker(database=FakeDatabase(), consumer_factory=factory)
        worker.consumer

        self.assertEqual(APPLICATION_WORKER_GROUP, "p16-application-worker")
        self.assertEqual(captured["topics"], APPLICATION_TOPICS)
        self.assertEqual(captured["config"].group_id, APPLICATION_WORKER_GROUP)

    def test_application_created_succeeds_and_writes_activity_log(self):
        database = FakeDatabase()
        consumer = FakeConsumer()
        result = ApplicationWorker(database=database).process_record(
            FakeRecord(self.make_envelope()),
            consumer=consumer,
            dlq_producer=FakeProducer(),
        )

        self.assertEqual(result.status, "processed")
        activity = database.collections["activity_logs"].documents[self.event_id]
        self.assertEqual(activity["event_id"], self.event_id)
        self.assertEqual(activity["event_type"], APPLICATION_CREATED)
        self.assertEqual(activity["trace_id"], self.trace_id)
        self.assertEqual(activity["actor"], {"user_id": 9, "role": "company"})
        self.assertEqual(activity["application_id"], 17)
        self.assertEqual(activity["job_id"], 8)
        self.assertEqual(activity["student_id"], 9)
        self.assertEqual(consumer.commits, 1)

    def test_application_updated_succeeds(self):
        database = FakeDatabase()
        result = ApplicationWorker(database=database).process_record(
            FakeRecord(self.make_envelope(APPLICATION_UPDATED)),
            consumer=FakeConsumer(),
            dlq_producer=FakeProducer(),
        )

        self.assertEqual(result.status, "processed")
        self.assertEqual(
            database.collections["activity_logs"].documents[self.event_id]["event_type"],
            APPLICATION_UPDATED,
        )

    def test_duplicate_event_is_skipped_and_activity_log_is_written_once(self):
        database = FakeDatabase()
        consumer = FakeConsumer()
        worker = ApplicationWorker(database=database)
        record = FakeRecord(self.make_envelope())
        worker.process_record(record, consumer=consumer, dlq_producer=FakeProducer())
        result = worker.process_record(
            record,
            consumer=consumer,
            dlq_producer=FakeProducer(),
        )

        self.assertEqual(result.status, "duplicate_skipped")
        self.assertEqual(database.collections["activity_logs"].calls, 1)
        self.assertEqual(database.collections["processed_events"].calls, 1)
        self.assertEqual(consumer.commits, 2)

    def test_processed_event_is_recorded_after_activity_log_and_before_commit(self):
        order = []
        database = FakeDatabase(order)
        consumer = FakeConsumer(order)
        result = ApplicationWorker(database=database).process_record(
            FakeRecord(self.make_envelope()),
            consumer=consumer,
            dlq_producer=FakeProducer(),
        )

        self.assertEqual(result.status, "processed")
        self.assertEqual(order, ["activity", "processed", "commit"])

    def test_activity_failure_retries_and_uses_dlq_without_commit_before_dlq(self):
        database = FakeDatabase(fail_activity=True)
        consumer = FakeConsumer()
        producer = FakeProducer()
        result = ApplicationWorker(database=database).process_record(
            FakeRecord(self.make_envelope()),
            consumer=consumer,
            dlq_producer=producer,
        )

        self.assertEqual(result.status, "dead_lettered")
        self.assertEqual(result.attempts, 3)
        self.assertEqual(consumer.commits, 1)
        self.assertEqual(producer.events[0][0], "p16.dlq")
        dlq = json.loads(producer.events[0][2])
        self.assertEqual(dlq["event_id"], self.event_id)
        self.assertEqual(dlq["trace_id"], self.trace_id)

    def test_unrelated_event_is_ignored_safely(self):
        database = FakeDatabase()
        consumer = FakeConsumer()
        result = ApplicationWorker(database=database).process_record(
            FakeRecord(self.make_envelope(MEMORY_CONSOLIDATE)),
            consumer=consumer,
            dlq_producer=FakeProducer(),
        )

        self.assertEqual(result.status, "processed")
        self.assertEqual(database.collections["activity_logs"].calls, 0)
        self.assertEqual(database.collections["processed_events"].calls, 1)
        self.assertEqual(consumer.commits, 1)

    def test_sensitive_values_are_not_logged(self):
        database = FakeDatabase(fail_activity=True)
        worker = ApplicationWorker(database=database)
        with self.assertLogs("app.messaging.consumer", level="WARNING") as captured:
            worker.process_record(
                FakeRecord(self.make_envelope()),
                consumer=FakeConsumer(),
                dlq_producer=FakeProducer(),
            )

        output = "\n".join(captured.output)
        self.assertNotIn("password", output)
        self.assertNotIn("do-not-log", output)


if __name__ == "__main__":
    import unittest

    unittest.main()
