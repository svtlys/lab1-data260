"""
company event creation and registration-view routes.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import require_company
from app.api.routes.company import find_company_profile
from app.core.database import get_db
from app.models.event import Event
from app.models.event_registration import EventRegistration
from app.models.student_profile import StudentProfile
from app.models.user import User
from app.schemas.company_event import (
    CompanyEventCreateRequest,
    CompanyEventResponse,
    EventRegistrationStudentResponse,
)
from app.services.eligibility import check_eligibility


# group company event endpoints under /api/companies/me/events
router = APIRouter(
    prefix="/api/companies/me/events",
    tags=["company events"],
)


def event_response(event: Event, registered_count: int) -> dict:
    """build a response with the count expected by the frontend."""

    return {
        "id": event.id,
        "company_id": event.company_id,
        "title": event.title,
        "description": event.description,
        "organizer": event.organizer,
        "location": event.location,
        "city": event.city,
        "event_date": event.event_date,
        "event_type": event.event_type,
        "is_virtual": event.is_virtual,
        "capacity": event.capacity,
        "eligible_majors": event.eligible_majors,
        "min_cgpa": event.min_cgpa,
        "min_grad_year": event.min_grad_year,
        "max_grad_year": event.max_grad_year,
        "eligibility_note": event.eligibility_note,
        "registered_count": registered_count,
        "created_at": event.created_at,
        "updated_at": event.updated_at,
    }


def count_registrations(event_id: int, db: Session) -> int:
    """count registrations without loading every student row."""

    return int(
        db.scalar(
            select(func.count(EventRegistration.id)).where(
                EventRegistration.event_id == event_id,
            )
        )
        or 0
    )


def find_owned_event(event_id: int, current_user: User, db: Session) -> Event:
    """find an event only when it belongs to the logged-in company."""

    company = find_company_profile(current_user, db)
    event = db.scalar(
        select(Event).where(
            Event.id == event_id,
            Event.company_id == company.id,
        )
    )
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="event was not found",
        )
    return event


@router.post(
    "",
    response_model=CompanyEventResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_company_event(
    request: CompanyEventCreateRequest,
    current_user: User = Depends(require_company),
    db: Session = Depends(get_db),
):
    """create an event owned by the logged-in company."""

    company = find_company_profile(current_user, db)
    event = Event(
        company_id=company.id,
        title=request.title,
        description=request.description,
        organizer=company.company_name,
        location="Online" if request.is_virtual else request.location,
        city=request.city,
        event_date=request.event_date,
        event_type=request.event_type,
        is_virtual=request.is_virtual,
        capacity=request.capacity,
        eligible_majors=request.eligible_majors,
        min_cgpa=request.min_cgpa,
        min_grad_year=request.min_grad_year,
        max_grad_year=request.max_grad_year,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event_response(event, 0)


@router.get(
    "",
    response_model=list[CompanyEventResponse],
)
def get_my_company_events(
    current_user: User = Depends(require_company),
    db: Session = Depends(get_db),
):
    """return only events owned by the logged-in company."""

    company = find_company_profile(current_user, db)
    events = db.scalars(
        select(Event)
        .where(Event.company_id == company.id)
        .order_by(Event.event_date.asc())
    ).all()
    return [event_response(event, count_registrations(event.id, db)) for event in events]


@router.get(
    "/{event_id}",
    response_model=CompanyEventResponse,
)
def get_my_company_event(
    event_id: int,
    current_user: User = Depends(require_company),
    db: Session = Depends(get_db),
):
    """return one event only when it belongs to the logged-in company."""

    event = find_owned_event(event_id, current_user, db)
    return event_response(event, count_registrations(event.id, db))


@router.get(
    "/{event_id}/registrations",
    response_model=list[EventRegistrationStudentResponse],
)
def get_event_registrations(
    event_id: int,
    current_user: User = Depends(require_company),
    db: Session = Depends(get_db),
):
    """return registered students and their eligibility results."""

    event = find_owned_event(event_id, current_user, db)
    rows = db.execute(
        select(EventRegistration, StudentProfile)
        .join(StudentProfile, StudentProfile.id == EventRegistration.student_id)
        .where(EventRegistration.event_id == event.id)
        .order_by(EventRegistration.registered_at.asc())
    ).all()

    results = []
    for registration, student in rows:
        eligible, reasons = check_eligibility(event, student)
        results.append(
            {
                "student_id": student.id,
                "student_name": student.full_name,
                "college_name": student.college_name,
                "major": student.major,
                "cgpa": student.cgpa,
                "graduation_year": student.graduation_year,
                "registered_at": registration.registered_at,
                "eligible": eligible,
                "ineligible_reasons": reasons,
            }
        )
    return results
