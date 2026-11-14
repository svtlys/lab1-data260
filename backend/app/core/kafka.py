"""lazy Kafka producer lifecycle for the opt-in Lab 2 foundation."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.core.config import Settings, settings


logger = logging.getLogger(__name__)
_producer: Any | None = None


class KafkaConfigurationError(RuntimeError):
    """indicate that Kafka producer configuration is not usable."""


def create_kafka_producer(config: Settings = settings) -> Any:
    """create one producer without connecting while the feature is disabled."""

    if not config.kafka_enabled:
        raise KafkaConfigurationError("kafka producer is disabled")

    from kafka import KafkaProducer

    bootstrap_servers = [
        server.strip()
        for server in config.kafka_bootstrap_servers.split(",")
        if server.strip()
    ]
    if not bootstrap_servers:
        raise KafkaConfigurationError("kafka bootstrap servers are not configured")

    return KafkaProducer(
        bootstrap_servers=bootstrap_servers,
        key_serializer=lambda value: value.encode("utf-8"),
        value_serializer=lambda value: value.encode("utf-8"),
        request_timeout_ms=config.kafka_request_timeout_ms,
    )


def get_kafka_producer(config: Settings = settings) -> Any | None:
    """return a shared producer only when Kafka is explicitly enabled."""

    global _producer
    if not config.kafka_enabled:
        return None
    if _producer is None:
        _producer = create_kafka_producer(config)
        logger.info("kafka producer initialized")
    return _producer


def close_kafka_producer() -> None:
    """flush and close the shared producer without exposing connection details."""

    global _producer
    if _producer is None:
        return
    try:
        _producer.flush(timeout=settings.kafka_publish_timeout_seconds)
        _producer.close()
        logger.info("kafka producer closed")
    finally:
        _producer = None
