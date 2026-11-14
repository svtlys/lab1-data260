"""test the memory worker with fake Kafka objects and the in-memory Mongo stand-in."""

from unittest import TestCase

from app.assistant.memory import InMemoryDatabase, add_memory, list_memories
from app.assistant.memory_seed import EXPECTED_AFTER, EXPECTED_BEFORE, seed_student_memory
from app.messaging.envelope import APPLICATION_STATUS_CHANGED, MEMORY_CONSOLIDATE, create_envelope
from app.workers.memory_worker import (
    MEMORY_TOPICS,
    MEMORY_WORKER_GROUP,
    MemoryWorker,
    handle_memory_consolidation,
)


class FakeRecord:
    def __init__(self, envelope):
        self.value = envelope.to_json()


class FakeConsumer:
    def __init__(self):
        self.commits = 0

    def commit(self):
        self.commits += 1


class FakeFuture:
    def get(self, timeout):
        return None


class FakeProducer:
    def __init__(self):
        self.sent = []

    def send(self, topic, key, value):
        self.sent.append((topic, key, value))
        return FakeFuture()


def consolidate_event(student_id, **extra):
    return create_envelope(MEMORY_CONSOLIDATE, {"student_id": student_id},
                           {"user_id": student_id, "role": "student"}, **extra)


class MemoryWorkerTests(TestCase):
    def setUp(self):
        self.database = InMemoryDatabase()
        seed_student_memory(self.database, 1)
        self.worker = MemoryWorker(database=self.database)
        self.consumer, self.producer = FakeConsumer(), FakeProducer()

    def process(self, envelope):
        return self.worker.process_record(
            FakeRecord(envelope), consumer=self.consumer, dlq_producer=self.producer
        )

    def test_topic_and_group_follow_the_design_decisions(self):
        self.assertEqual(MEMORY_TOPICS, ("p16.memory.consolidate",))
        self.assertEqual(MEMORY_WORKER_GROUP, "p16-memory-worker")
        self.assertEqual(self.worker.config.group_id, "p16-memory-worker")

    def test_event_consolidates_memory_and_commits_after_the_work(self):
        result = self.process(consolidate_event(1))

        self.assertEqual(result.status, "processed")
        self.assertTrue(result.offset_committed)
        self.assertEqual(self.consumer.commits, 1)
        self.assertEqual(len(list_memories(self.database, 1)), EXPECTED_AFTER)

    def test_activity_log_carries_the_trace_id_and_counts(self):
        envelope = consolidate_event(1)
        self.process(envelope)

        log = self.database["activity_logs"].find_one({"_id": str(envelope.event_id)})
        self.assertEqual(log["trace_id"], str(envelope.trace_id))
        self.assertEqual((log["before"], log["after"]), (EXPECTED_BEFORE, EXPECTED_AFTER))
        self.assertEqual(log["activity_type"], "memory_consolidation")

    def test_the_same_event_twice_is_skipped_the_second_time(self):
        envelope = consolidate_event(1)
        self.process(envelope)
        add_memory(self.database, 1, "note", "added after the first run")
        before = len(list_memories(self.database, 1))

        second = self.process(envelope)

        self.assertEqual(second.status, "duplicate_skipped")
        self.assertEqual(len(list_memories(self.database, 1)), before)
        self.assertEqual(self.consumer.commits, 2)

    def test_bad_event_is_retried_three_times_then_dead_lettered(self):
        bad = create_envelope(MEMORY_CONSOLIDATE, {"student_id": "not a number"}, {"user_id": 1, "role": "student"})
        result = self.process(bad)

        self.assertEqual(result.status, "dead_lettered")
        self.assertEqual(result.attempts, 3)
        self.assertEqual(self.producer.sent[0][0], "p16.dlq")
        self.assertEqual(len(list_memories(self.database, 1)), EXPECTED_BEFORE)

    def test_other_event_types_are_ignored(self):
        other = create_envelope(APPLICATION_STATUS_CHANGED, {"student_id": 1}, {"user_id": 1, "role": "student"})
        self.assertFalse(handle_memory_consolidation(other, self.database))
        self.assertEqual(len(list_memories(self.database, 1)), EXPECTED_BEFORE)
