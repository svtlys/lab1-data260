"""manual-commit Kafka consumer reliability foundation."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Iterable

from app.messaging.envelope import EventEnvelope, create_envelope
from app.messaging.idempotency import is_event_processed, record_event_processed


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class KafkaConsumerConfig:
    """configure a manual-commit consumer without holding credentials."""

    bootstrap_servers: str = "p16-kafka:9092"
    group_id: str = "p16-lab2-consumer"
    topic_prefix: str = "p16"
    auto_offset_reset: str = "earliest"
    max_attempts: int = 3
    publish_timeout_seconds: float = 5.0

    def __post_init__(self) -> None:
        if not self.bootstrap_servers.strip():
            raise ValueError("bootstrap_servers is required")
        if not self.group_id.strip():
            raise ValueError("group_id is required")
        if not self.topic_prefix.strip():
            raise ValueError("topic_prefix is required")
        if self.max_attempts < 1 or self.max_attempts > 3:
            raise ValueError("max_attempts must be between 1 and 3")


@dataclass(frozen=True)
class ProcessingResult:
    """describe one record outcome without exposing message contents."""

    status: str
    attempts: int
    offset_committed: bool


def topic_name(topic_suffix: str, config: KafkaConsumerConfig) -> str:
    """construct a topic name from the configured prefix."""

    suffix = topic_suffix.strip().strip(".")
    prefix = config.topic_prefix.strip().strip(".")
    if not suffix or not prefix:
        raise ValueError("topic name parts are required")
    return suffix if suffix == prefix or suffix.startswith(f"{prefix}.") else f"{prefix}.{suffix}"


def create_consumer(
    topics: Iterable[str],
    config: KafkaConsumerConfig = KafkaConsumerConfig(),
) -> Any:
    """create a Kafka consumer with auto-commit explicitly disabled."""

    from kafka import KafkaConsumer

    return KafkaConsumer(
        *tuple(topics),
        bootstrap_servers=config.bootstrap_servers,
        group_id=config.group_id,
        enable_auto_commit=False,
        auto_offset_reset=config.auto_offset_reset,
    )


def decode_envelope(value: Any) -> EventEnvelope:
    """validate a Kafka value using the agreed event envelope."""

    if isinstance(value, EventEnvelope):
        return value
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    if isinstance(value, str):
        value = json.loads(value)
    return EventEnvelope.model_validate(value)


def build_dlq_envelope(
    envelope: EventEnvelope,
    attempts: int,
) -> EventEnvelope:
    """wrap the original envelope with sanitized failure metadata."""

    return create_envelope(
        envelope.event_type,
        {
            "original_envelope": envelope.to_dict(),
            "failure": {
                "attempts": attempts,
                "reason": "handler_failed",
            },
        },
        envelope.actor,
        event_id=envelope.event_id,
        trace_id=envelope.trace_id,
        occurred_at=envelope.occurred_at,
    )


def publish_to_dlq(
    producer: Any,
    envelope: EventEnvelope,
    attempts: int,
    config: KafkaConsumerConfig,
) -> EventEnvelope:
    """publish a failed event to the prefixed dead-letter topic."""

    dlq_envelope = build_dlq_envelope(envelope, attempts)
    future = producer.send(
        topic_name("dlq", config),
        key=str(envelope.event_id),
        value=dlq_envelope.to_json(),
    )
    future.get(timeout=config.publish_timeout_seconds)
    return dlq_envelope


def process_record(
    record: Any,
    *,
    database: Any,
    handler: Callable[[EventEnvelope], Any],
    consumer: Any,
    dlq_producer: Any,
    config: KafkaConsumerConfig = KafkaConsumerConfig(),
) -> ProcessingResult:
    """process one record with idempotency, retries, DLQ, and manual commit."""

    envelope = decode_envelope(record.value)
    if is_event_processed(database, str(envelope.event_id)):
        consumer.commit()
        return ProcessingResult("duplicate_skipped", 0, True)

    for attempt in range(1, config.max_attempts + 1):
        try:
            handler(envelope)
            record_event_processed(database, envelope)
            consumer.commit()
            return ProcessingResult("processed", attempt, True)
        except Exception:
            if attempt < config.max_attempts:
                logger.warning("kafka event processing failed; retrying")
                continue

            try:
                publish_to_dlq(dlq_producer, envelope, attempt, config)
                consumer.commit()
                return ProcessingResult("dead_lettered", attempt, True)
            except Exception:
                logger.error("kafka dlq publish failed; offset remains uncommitted")
                return ProcessingResult("dlq_failed", attempt, False)

    return ProcessingResult("failed", config.max_attempts, False)
