"""Kafka worker that consolidates a student's assistant memory (topic p16.memory.consolidate)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable

from app.assistant.memory import ACTIVITY_COLLECTION, consolidate_student
from app.core.mongo import get_mongo_database
from app.messaging.consumer import (
    KafkaConsumerConfig,
    ProcessingResult,
    create_consumer,
    process_record as process_kafka_record,
)
from app.messaging.envelope import MEMORY_CONSOLIDATE, EventEnvelope


logger = logging.getLogger(__name__)

MEMORY_TOPICS = ("p16.memory.consolidate",)
MEMORY_WORKER_GROUP = "p16-memory-worker"
MEMORY_WORKER_CONFIG = KafkaConsumerConfig(group_id=MEMORY_WORKER_GROUP)


def handle_memory_consolidation(envelope: EventEnvelope, database: Any) -> bool:
    """consolidate one student's memory and log what happened (carrying the event's trace id)."""

    if envelope.event_type != MEMORY_CONSOLIDATE:
        logger.info("memory worker ignored an unsupported event type")
        return False

    student_id = envelope.payload.get("student_id")
    if isinstance(student_id, bool) or not isinstance(student_id, int):
        raise ValueError("memory consolidation student id is invalid")

    summary = consolidate_student(database, student_id)
    logger.info(
        "memory_consolidated student_id=%s before=%s after=%s trace_id=%s",
        student_id, summary["before"], summary["after"], envelope.trace_id,
    )
    database[ACTIVITY_COLLECTION].update_one(
        {"_id": str(envelope.event_id)},
        {"$setOnInsert": {
            "_id": str(envelope.event_id),
            "event_id": str(envelope.event_id),
            "event_type": envelope.event_type,
            "trace_id": str(envelope.trace_id),
            "activity_type": "memory_consolidation",
            "student_id": student_id,
            "before": summary["before"],
            "after": summary["after"],
            "duplicates_removed": summary["duplicates"],
            "contradictions_resolved": summary["contradictions"],
            "processed_at": datetime.now(timezone.utc),
        }},
        upsert=True,
    )
    return True


class MemoryWorker:
    """lazily connect and consolidate memory with the shared retry, DLQ and idempotency rules."""

    def __init__(
        self,
        database: Any | None = None,
        *,
        consumer_factory: Callable[..., Any] = create_consumer,
    ) -> None:
        self._database = database
        self._consumer_factory = consumer_factory
        self._consumer: Any | None = None
        self._dlq_producer: Any | None = None
        self.config = MEMORY_WORKER_CONFIG

    @property
    def database(self) -> Any:
        if self._database is None:
            self._database = get_mongo_database()
        if self._database is None:
            raise RuntimeError("mongo database is unavailable")
        return self._database

    @property
    def consumer(self) -> Any:
        if self._consumer is None:
            self._consumer = self._consumer_factory(MEMORY_TOPICS, self.config)
        return self._consumer

    @property
    def dlq_producer(self) -> Any:
        if self._dlq_producer is None:
            from app.core.config import settings
            from app.core.kafka import get_kafka_producer

            self._dlq_producer = get_kafka_producer(settings)
        return self._dlq_producer

    def process_record(
        self,
        record: Any,
        *,
        consumer: Any | None = None,
        dlq_producer: Any | None = None,
    ) -> ProcessingResult:
        """process one record through the shared foundation (idempotent, 3 tries, then the DLQ)."""

        return process_kafka_record(
            record,
            database=self.database,
            handler=lambda envelope: handle_memory_consolidation(envelope, self.database),
            consumer=consumer if consumer is not None else self.consumer,
            dlq_producer=dlq_producer if dlq_producer is not None else self.dlq_producer,
            config=self.config,
        )

    def run(self) -> None:
        """consume consolidation events until stopped."""

        consumer = self.consumer
        try:
            for record in consumer:
                self.process_record(record)
        finally:
            close = getattr(consumer, "close", None)
            if close is not None:
                close()


def main() -> None:
    """run the memory worker process (container entry point)."""

    MemoryWorker().run()


if __name__ == "__main__":
    main()
