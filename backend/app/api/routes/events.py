"""
student event search, details, and registration routes.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import require_student
from app.core.database import get_db
from app.models.event import Event
from app.models.event_registration import EventRegistration
from app.models.student_profile import StudentProfile
from app.models.user import User
from app.schemas.event import EventRegistrationResponse, EventResponse


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

    return registration
