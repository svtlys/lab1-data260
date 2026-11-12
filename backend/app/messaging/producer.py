"""optional Kafka publish helper for validated event envelopes."""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import Settings, settings
from app.core.kafka import get_kafka_producer
from app.messaging.envelope import EventEnvelope, kafka_key


logger = logging.getLogger(__name__)


class KafkaPublishError(RuntimeError):
    """indicate a sanitized Kafka publish failure."""


def topic_name(topic_suffix: str, config: Settings = settings) -> str:
    """construct a topic name from the configured prefix and suffix."""

    if not isinstance(topic_suffix, str) or not topic_suffix.strip():
        raise ValueError("topic suffix is required")
    suffix = topic_suffix.strip().strip(".")
    prefix = config.kafka_topic_prefix.strip().strip(".")
    if not prefix:
        raise ValueError("kafka topic prefix is required")
    if suffix == prefix or suffix.startswith(f"{prefix}."):
        return suffix
    return f"{prefix}.{suffix}"


def publish_event(
    envelope: EventEnvelope,
    topic_suffix: str,
    related_entity_id: int,
    *,
    config: Settings = settings,
) -> dict[str, Any]:
    """publish one validated envelope or return a safe disabled result."""

    if not isinstance(envelope, EventEnvelope):
        raise TypeError("envelope must be an EventEnvelope")

    topic = topic_name(topic_suffix, config)
    key = kafka_key(related_entity_id)
    producer = get_kafka_producer(config)
    if producer is None:
        logger.info("kafka publish skipped because the producer is disabled")
        return {
            "status": "disabled",
            "published": False,
            "topic": topic,
        }

    try:
        future = producer.send(topic, key=key, value=envelope.to_json())
        future.get(timeout=config.kafka_publish_timeout_seconds)
    except Exception as error:
        logger.error("kafka publish failed for event type %s", envelope.event_type)
        raise KafkaPublishError("kafka publish failed") from error

    logger.info("kafka event published for event type %s", envelope.event_type)
    return {
        "status": "published",
        "published": True,
        "topic": topic,
        "event_id": str(envelope.event_id),
        "key": key,
    }
