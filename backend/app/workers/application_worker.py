"""Kafka worker for application audit events."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable, Iterable

from app.core.mongo import get_mongo_database
from app.messaging.consumer import (
    KafkaConsumerConfig,
    ProcessingResult,
    create_consumer,
    process_record as process_kafka_record,
)
from app.messaging.envelope import (
    APPLICATION_CREATED,
    APPLICATION_UPDATED,
    EventEnvelope,
)


logger = logging.getLogger(__name__)

CONSUMED_EVENT_TYPES = frozenset({APPLICATION_CREATED, APPLICATION_UPDATED})
APPLICATION_TOPICS = (
    "p16.application.created",
    "p16.application.updated",
)
APPLICATION_WORKER_GROUP = "p16-application-worker"
APPLICATION_WORKER_CONFIG = KafkaConsumerConfig(
    group_id=APPLICATION_WORKER_GROUP,
)


def _required_integer(payload: dict[str, Any], field_name: str) -> int:
    """return one required numeric relationship id."""

    value = payload.get(field_name)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("application event relationship id is invalid")
    return value


def handle_application_event(
    envelope: EventEnvelope,
    database: Any,
) -> bool:
    """write one sanitized activity log for a supported application event."""

    if envelope.event_type not in CONSUMED_EVENT_TYPES:
        logger.info("application worker ignored an unsupported event type")
        return False

    payload = envelope.payload
    processed_at = datetime.now(timezone.utc)
    activity_log = {
        "_id": str(envelope.event_id),
        "event_id": str(envelope.event_id),
        "event_type": envelope.event_type,
        "trace_id": str(envelope.trace_id),
        "actor": envelope.actor.model_dump(mode="json"),
        "application_id": _required_integer(payload, "application_id"),
        "job_id": _required_integer(payload, "job_id"),
        "student_id": _required_integer(payload, "student_id"),
        "occurred_at": envelope.occurred_at,
        "processed_at": processed_at,
    }
    for field_name in ("status", "previous_status", "new_status"):
        if field_name in payload:
            activity_log[field_name] = payload[field_name]

    database["activity_logs"].update_one(
        {"_id": str(envelope.event_id)},
        {"$setOnInsert": activity_log},
        upsert=True,
    )
    return True


class ApplicationWorker:
    """lazily connect and process application events with shared reliability."""

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
        self.config = APPLICATION_WORKER_CONFIG

    @property
    def database(self) -> Any:
        """lazily resolve the configured Mongo database."""

        if self._database is None:
            self._database = get_mongo_database()
        if self._database is None:
            raise RuntimeError("mongo database is unavailable")
        return self._database

    @property
    def consumer(self) -> Any:
        """lazily create the distinct application consumer group."""

        if self._consumer is None:
            self._consumer = self._consumer_factory(APPLICATION_TOPICS, self.config)
        return self._consumer

    @property
    def dlq_producer(self) -> Any:
        """lazily resolve the shared Kafka producer for DLQ publishing."""

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
        """process one application record through the shared foundation."""

        active_consumer = consumer if consumer is not None else self.consumer
        active_dlq_producer = (
            dlq_producer if dlq_producer is not None else self.dlq_producer
        )
        return process_kafka_record(
            record,
            database=self.database,
            handler=lambda envelope: handle_application_event(
                envelope,
                self.database,
            ),
            consumer=active_consumer,
            dlq_producer=active_dlq_producer,
            config=self.config,
        )

    def run(self) -> None:
        """consume application events until the future worker stops."""

        consumer = self.consumer
        try:
            for record in consumer:
                self.process_record(record)
        finally:
            close = getattr(consumer, "close", None)
            if close is not None:
                close()


def run_application_worker() -> None:
    """provide a future container entry point without eager connections."""

    ApplicationWorker().run()


def main() -> None:
    """run the application worker process."""

    run_application_worker()


if __name__ == "__main__":
    main()
