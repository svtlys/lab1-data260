"""MongoDB-backed idempotency helpers for Kafka consumers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.messaging.envelope import EventEnvelope


PROCESSED_EVENTS_COLLECTION = "processed_events"


def is_event_processed(database: Any, event_id: str) -> bool:
    """return whether the event id already has a processed record."""

    return (
        database[PROCESSED_EVENTS_COLLECTION].find_one(
            {"event_id": str(event_id)}
        )
        is not None
    )


def record_event_processed(database: Any, envelope: EventEnvelope) -> None:
    """record sanitized event metadata after handler work succeeds."""

    database[PROCESSED_EVENTS_COLLECTION].update_one(
        {"event_id": str(envelope.event_id)},
        {
            "$setOnInsert": {
                "event_id": str(envelope.event_id),
                "event_type": envelope.event_type,
                "trace_id": str(envelope.trace_id),
                "processed_at": datetime.now(timezone.utc),
            }
        },
        upsert=True,
    )
