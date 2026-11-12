"""typed and validated Kafka event envelopes."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, ClassVar
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator
from pydantic.types import StrictInt, StrictStr


APPLICATION_CREATED = "application.created"
APPLICATION_UPDATED = "application.updated"
APPLICATION_STATUS_CHANGED = "application.status_changed"
EVENT_REGISTRATION_CREATED = "event.registration_created"
JOB_CREATED = "job.created"
MEMORY_CONSOLIDATE = "memory.consolidate"

EVENT_TYPES = frozenset(
    {
        APPLICATION_CREATED,
        APPLICATION_UPDATED,
        APPLICATION_STATUS_CHANGED,
        EVENT_REGISTRATION_CREATED,
        JOB_CREATED,
        MEMORY_CONSOLIDATE,
    }
)


class Actor(BaseModel):
    """identify the authenticated actor without credentials."""

    model_config = ConfigDict(extra="forbid")

    user_id: StrictInt | None
    role: StrictStr | None


class EventEnvelope(BaseModel):
    """represent one validated event sent between Lab 2 services."""

    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    event_type: StrictStr
    occurred_at: datetime
    trace_id: UUID
    actor: Actor
    payload: dict[str, Any] = Field(min_length=0)

    allowed_event_types: ClassVar[frozenset[str]] = EVENT_TYPES

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, value: str) -> str:
        """reject event names outside the agreed Lab 2 contract."""

        if value not in cls.allowed_event_types:
            raise ValueError("event_type is not supported")
        return value

    @field_validator("occurred_at", mode="before")
    @classmethod
    def normalize_utc_timestamp(cls, value: Any) -> datetime:
        """require an aware timestamp and normalize it to UTC."""

        if isinstance(value, str):
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if not isinstance(value, datetime) or value.tzinfo is None:
            raise ValueError("occurred_at must be a timezone-aware UTC timestamp")
        return value.astimezone(timezone.utc)

    @field_validator("payload")
    @classmethod
    def validate_json_payload(cls, value: dict[str, Any]) -> dict[str, Any]:
        """ensure the payload can be serialized as a JSON object."""

        try:
            json.dumps(value)
        except (TypeError, ValueError) as error:
            raise ValueError("payload must be JSON serializable") from error
        return value

    @field_serializer("occurred_at")
    def serialize_utc_timestamp(self, value: datetime) -> str:
        """serialize every timestamp with a UTC Z suffix."""

        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    def to_dict(self) -> dict[str, Any]:
        """return a Kafka-ready JSON-compatible dictionary."""

        return self.model_dump(mode="json")

    def to_json(self) -> str:
        """return stable JSON for a Kafka message value."""

        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))


def create_envelope(
    event_type: str,
    payload: dict[str, Any],
    actor: Actor | dict[str, Any],
    *,
    trace_id: UUID | str | None = None,
    event_id: UUID | str | None = None,
    occurred_at: datetime | None = None,
) -> EventEnvelope:
    """create an envelope with generated IDs and a UTC timestamp by default."""

    return EventEnvelope(
        event_id=event_id or uuid4(),
        event_type=event_type,
        occurred_at=occurred_at or datetime.now(timezone.utc),
        trace_id=trace_id or uuid4(),
        actor=actor,
        payload=payload,
    )


def kafka_key(related_entity_id: int) -> str:
    """return the related numeric entity ID in Kafka key format."""

    if isinstance(related_entity_id, bool) or not isinstance(related_entity_id, int):
        raise TypeError("related_entity_id must be an integer")
    return str(related_entity_id)
