"""
student event search, details, and registration routes.
"""

import logging
import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from bson.decimal128 import Decimal128
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import require_student
from app.core.config import settings
from app.core.database import get_db
from app.core.mongo import get_mongo_database
from app.messaging.envelope import EVENT_REGISTRATION_CREATED, create_envelope
from app.messaging.producer import publish_event
from app.models.event import Event
from app.models.event_registration import EventRegistration
from app.models.student_profile import StudentProfile
from app.models.user import User
from app.schemas.event import EventRegistrationResponse, EventResponse
from app.services.eligibility import check_eligibility, check_registration_open


logger = logging.getLogger(__name__)


# group student event endpoints under /api/events
router = APIRouter(
    prefix="/api/events",
    tags=["events"],
)


def find_student_profile(current_user: User, db: Session) -> StudentProfile:
    """find the profile belonging to the logged-in student."""

    profile = db.scalar(
        select(StudentProfile).where(
            StudentProfile.user_id == current_user.id,
        )
    )

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="student profile was not found",
        )

    return profile


def _mongo_event_value(value: Any, field_name: str) -> Any:
    """convert Mongo event values to the existing response types."""

    if isinstance(value, Decimal128):
        return float(value.to_decimal()) if field_name == "min_cgpa" else value.to_decimal()
    if isinstance(value, Decimal):
        return float(value) if field_name == "min_cgpa" else value
    return value


def mongo_event_response(
    event: dict[str, Any],
    registered_count: int = 0,
) -> dict[str, Any]:
    """map one Mongo event to the student event response shape."""

    return {
        "id": int(event["id"]),
        "company_id": event.get("company_id"),
        "title": event["title"],
        "description": event["description"],
        "organizer": event["organizer"],
        "location": event["location"],
        "city": event["city"],
        "event_date": event["event_date"],
        "event_type": event["event_type"],
        "is_virtual": event["is_virtual"],
        "capacity": event.get("capacity"),
        "eligible_majors": event.get("eligible_majors"),
        "min_cgpa": _mongo_event_value(event.get("min_cgpa"), "min_cgpa"),
        "min_grad_year": event.get("min_grad_year"),
        "max_grad_year": event.get("max_grad_year"),
        "eligibility_note": event.get("eligibility_note"),
        "registered_count": int(registered_count),
        "created_at": event["created_at"],
        "updated_at": event["updated_at"],
    }


def _get_mongo_event_database() -> Any | None:
    """return Mongo for event reads without leaking connection errors."""

    try:
        return get_mongo_database()
    except Exception:
        return None


def _search_events_from_mongo(
    city: str | None,
    event_type: str | None,
    is_virtual: bool | None,
    start_date: datetime | None,
    end_date: datetime | None,
    search: str | None,
) -> list[dict[str, Any]] | None:
    """search Mongo events or signal SQL fallback."""

    database = _get_mongo_event_database()
    if database is None:
        return None
    try:
        filters: dict[str, Any] = {}
        if city:
            filters["city"] = city
        if event_type:
            filters["event_type"] = event_type
        if is_virtual is not None:
            filters["is_virtual"] = is_virtual
        if start_date:
            filters["event_date"] = {"$gte": start_date}
        if end_date:
            filters.setdefault("event_date", {})["$lte"] = end_date
        if search:
            filters["$or"] = [
                {field: {"$regex": re.escape(search), "$options": "i"}}
                for field in ("title", "description", "organizer")
            ]
        events = database["events"].find(filters).sort("event_date", 1)
        return [mongo_event_response(event) for event in events]
    except Exception:
        return None


def _get_event_from_mongo(event_id: int) -> tuple[bool, dict[str, Any] | None]:
    """return Mongo availability and one event without exposing Mongo errors."""

    database = _get_mongo_event_database()
    if database is None:
        return False, None
    try:
        event = database["events"].find_one({"id": event_id})
        return True, None if event is None else mongo_event_response(event)
    except Exception:
        return False, None


def _get_registered_events_from_mongo(
    user_id: int,
) -> tuple[bool, list[dict[str, Any]] | None]:
    """return a student's registered Mongo events or signal SQL fallback."""

    database = _get_mongo_event_database()
    if database is None:
        return False, None
    try:
        student = database["student_profiles"].find_one({"user_id": user_id})
        if student is None:
            return True, None
        registrations = database["event_registrations"].find(
            {"student_id": student["id"]}
        )
        events = []
        for registration in registrations:
            event = database["events"].find_one({"id": registration["event_id"]})
            if event is not None:
                events.append(event)
        events.sort(key=lambda event: event["event_date"])
        return True, [mongo_event_response(event) for event in events]
    except Exception:
        return False, None


@router.get("", response_model=list[EventResponse])
def search_events(
    city: str | None = Query(default=None, max_length=100),
    event_type: str | None = Query(default=None, max_length=100),
    is_virtual: bool | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    search: str | None = Query(default=None, max_length=100),
    current_user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    """search events using optional filters for the logged-in student."""

    mongo_events = _search_events_from_mongo(
        city,
        event_type,
        is_virtual,
        start_date,
        end_date,
        search,
    )
    if mongo_events is not None:
        return mongo_events

    # begin with every event and add only the filters the student selected
    statement = select(Event)

    if city:
        statement = statement.where(Event.city == city)

    if event_type:
        statement = statement.where(Event.event_type == event_type)

    if is_virtual is not None:
        statement = statement.where(Event.is_virtual == is_virtual)

    if start_date:
        statement = statement.where(Event.event_date >= start_date)

    if end_date:
        statement = statement.where(Event.event_date <= end_date)

    if search:
        search_pattern = f"%{search}%"
        statement = statement.where(
            Event.title.like(search_pattern)
            | Event.description.like(search_pattern)
            | Event.organizer.like(search_pattern)
        )

    # show the soonest events first for a useful student experience
    statement = statement.order_by(Event.event_date.asc())

    return list(db.scalars(statement).all())


@router.get("/registered", response_model=list[EventResponse])
def get_registered_events(
    current_user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    """return all events registered by the logged-in student."""

    mongo_available, mongo_events = _get_registered_events_from_mongo(
        current_user.id
    )
    if mongo_available:
        if mongo_events is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="student profile was not found",
            )
        return mongo_events

    student_profile = find_student_profile(current_user, db)
    statement = (
        select(Event)
        .join(EventRegistration)
        .where(EventRegistration.student_id == student_profile.id)
        .order_by(Event.event_date.asc())
    )

    return list(db.scalars(statement).all())


@router.get("/{event_id}", response_model=EventResponse)
def get_event_details(
    event_id: int,
    current_user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    """return details for one event."""

    mongo_available, mongo_event = _get_event_from_mongo(event_id)
    if mongo_available:
        if mongo_event is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="event was not found",
            )
        return mongo_event

    event = db.get(Event, event_id)

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="event was not found",
        )

    return event


@router.post(
    "/{event_id}/register",
    response_model=EventRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_for_event(
    event_id: int,
    current_user: User = Depends(require_student),
    db: Session = Depends(get_db),
    http_request: Request = None,
):
    """register the logged-in student for one event."""

    event = db.get(Event, event_id)

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="event was not found",
        )

    student_profile = find_student_profile(current_user, db)
    existing_registration = db.scalar(
        select(EventRegistration).where(
            EventRegistration.event_id == event.id,
            EventRegistration.student_id == student_profile.id,
        )
    )

    if existing_registration is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="you are already registered for this event",
        )

    if event.company_id is not None:
        eligible, reasons = check_eligibility(event, student_profile)
        if not eligible:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="; ".join(reasons),
            )

        registered_count = db.scalar(
            select(func.count(EventRegistration.id)).where(
                EventRegistration.event_id == event.id,
            )
        ) or 0
        registration_open, reason = check_registration_open(event, int(registered_count))
        if not registration_open:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=reason,
            )

    registration = EventRegistration(
        event_id=event.id,
        student_id=student_profile.id,
    )
    db.add(registration)

    try:
        db.commit()
        db.refresh(registration)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="you are already registered for this event",
        ) from error

    if settings.kafka_enabled:
        try:
            registered_at = registration.registered_at
            if registered_at.tzinfo is None:
                registered_at = registered_at.replace(tzinfo=timezone.utc)
            registered_at = registered_at.astimezone(timezone.utc)
            trace_id = http_request.headers.get("X-Trace-Id") if http_request else None
            envelope = create_envelope(
                EVENT_REGISTRATION_CREATED,
                {
                    "registration_id": registration.id,
                    "event_id": registration.event_id,
                    "student_id": registration.student_id,
                    "registered_at": registered_at.isoformat().replace("+00:00", "Z"),
                },
                {
                    "user_id": current_user.id,
                    "role": current_user.role.value,
                },
                trace_id=trace_id,
            )
            publish_event(
                envelope,
                "event.registration_created",
                event.id,
            )
        except Exception:
            logger.error(
                "event.registration_created event was not published; committed MySQL registration remains"
            )

    return registration
