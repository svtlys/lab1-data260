"""
request and response schemas for student events.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EventResponse(BaseModel):
    """return event information to a student."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    organizer: str
    location: str
    city: str
    event_date: datetime
    event_type: str
    is_virtual: bool
    capacity: int | None = Field(default=None, ge=1)
    created_at: datetime
    updated_at: datetime


class EventRegistrationResponse(BaseModel):
    """return confirmation information after registration."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: int
    student_id: int
    registered_at: datetime
