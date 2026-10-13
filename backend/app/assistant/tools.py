"""
manual database tools for the Week 3 assistant.

these functions are intentionally ordinary Python functions. the assistant
loop will decide when to call them without using an agent framework.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.event import Event
from app.models.job import Job
from app.models.saved_item import SavedItem
from app.models.student_profile import StudentProfile


class AssistantToolError(ValueError):
    """represent invalid input supplied to an assistant tool."""


def _json_value(value: Any) -> Any:
    """convert database values into values safe for tool responses."""

    if isinstance(value, (datetime, Decimal)):
        return str(value)

    return value


def _student_preferences_dict(profile: StudentProfile) -> dict[str, Any]:
    """convert a student profile into assistant-friendly preferences."""

    preference_fields = (
        "full_name",
        "college_name",
        "career_objective",
        "city",
        "state",
        "country",
        "degree",
        "major",
        "graduation_year",
        "cgpa",
        "experience",
        "skills",
    )

    return {
        field_name: _json_value(getattr(profile, field_name))
        for field_name in preference_fields
    }


def _job_dict(job: Job) -> dict[str, Any]:
    """convert one job model into an assistant result."""

    return {
        "id": job.id,
        "title": job.title,
        "description": job.description,
        "company_name": job.company_name,
        "location": job.location,
        "city": job.city,
        "employment_type": job.employment_type,
        "is_remote": job.is_remote,
        "salary_min": _json_value(job.salary_min),
        "salary_max": _json_value(job.salary_max),
        "required_skills": job.required_skills,
        "posted_at": _json_value(job.posted_at),
    }


def _event_dict(event: Event) -> dict[str, Any]:
    """convert one event model into an assistant result."""

    return {
        "id": event.id,
        "title": event.title,
        "description": event.description,
        "organizer": event.organizer,
        "location": event.location,
        "city": event.city,
        "event_date": _json_value(event.event_date),
        "event_type": event.event_type,
        "is_virtual": event.is_virtual,
        "capacity": event.capacity,
    }


def _parse_datetime(value: datetime | str | None) -> datetime | None:
    """parse an optional ISO datetime supplied by the assistant."""

    if value is None or isinstance(value, datetime):
        return value

    try:
        return datetime.fromisoformat(value)
    except ValueError as error:
        raise AssistantToolError(
            "date filters must use ISO format such as 2026-10-20T18:00:00"
        ) from error


def get_student_preferences(
    db: Session,
    student_id: int,
) -> dict[str, Any]:
    """return the profile preferences for one student."""

    profile = db.scalar(
        select(StudentProfile).where(StudentProfile.user_id == student_id)
    )

    if profile is None:
        raise AssistantToolError("student preferences were not found")

    return _student_preferences_dict(profile)


def search_jobs(
    db: Session,
    query: str | None = None,
    city: str | None = None,
    employment_type: str | None = None,
    is_remote: bool | None = None,
    required_skill: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """search seeded jobs using optional student-friendly filters."""

    if limit < 1 or limit > 50:
        raise AssistantToolError("limit must be between 1 and 50")

    statement = select(Job)

    if query:
        search_pattern = f"%{query}%"
        statement = statement.where(
            or_(
                Job.title.like(search_pattern),
                Job.description.like(search_pattern),
                Job.company_name.like(search_pattern),
            )
        )

    if city:
        statement = statement.where(Job.city == city)

    if employment_type:
        statement = statement.where(Job.employment_type == employment_type)

    if is_remote is not None:
        statement = statement.where(Job.is_remote == is_remote)

    if required_skill:
        statement = statement.where(
            Job.required_skills.like(f"%{required_skill}%")
        )

    statement = statement.order_by(Job.posted_at.desc()).limit(limit)
    return [_job_dict(job) for job in db.scalars(statement).all()]


def get_job_details(
    db: Session,
    job_id: int,
) -> dict[str, Any]:
    """return details for one job."""

    job = db.get(Job, job_id)

    if job is None:
        raise AssistantToolError("job was not found")

    return _job_dict(job)


def search_events(
    db: Session,
    query: str | None = None,
    city: str | None = None,
    event_type: str | None = None,
    is_virtual: bool | None = None,
    start_date: datetime | str | None = None,
    end_date: datetime | str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """search events using optional student-friendly filters."""

    if limit < 1 or limit > 50:
        raise AssistantToolError("limit must be between 1 and 50")

    start_datetime = _parse_datetime(start_date)
    end_datetime = _parse_datetime(end_date)
    statement = select(Event)

    if query:
        search_pattern = f"%{query}%"
        statement = statement.where(
            or_(
                Event.title.like(search_pattern),
                Event.description.like(search_pattern),
                Event.organizer.like(search_pattern),
            )
        )

    if city:
        statement = statement.where(Event.city == city)

    if event_type:
        statement = statement.where(Event.event_type == event_type)

    if is_virtual is not None:
        statement = statement.where(Event.is_virtual == is_virtual)

    if start_datetime:
        statement = statement.where(Event.event_date >= start_datetime)

    if end_datetime:
        statement = statement.where(Event.event_date <= end_datetime)

    statement = statement.order_by(Event.event_date.asc()).limit(limit)
    return [_event_dict(event) for event in db.scalars(statement).all()]


def save_job_or_event(
    db: Session,
    student_id: int,
    item_type: str,
    item_id: int,
) -> dict[str, Any]:
    """save one job or event for a student without creating duplicates."""

    normalized_item_type = item_type.strip().lower()

    if normalized_item_type not in {"job", "event"}:
        raise AssistantToolError("item_type must be either job or event")

    student_exists = db.scalar(
        select(StudentProfile.id).where(StudentProfile.user_id == student_id)
    )

    if student_exists is None:
        raise AssistantToolError("student preferences were not found")

    lookup_field = (
        SavedItem.job_id
        if normalized_item_type == "job"
        else SavedItem.event_id
    )
    existing_item = db.scalar(
        select(SavedItem).where(
            SavedItem.student_id == student_exists,
            lookup_field == item_id,
        )
    )

    if existing_item is not None:
        return {
            "saved": True,
            "already_saved": True,
            "item_type": normalized_item_type,
            "item_id": item_id,
        }

    if normalized_item_type == "job":
        item_exists = db.get(Job, item_id)
    else:
        item_exists = db.get(Event, item_id)

    if item_exists is None:
        raise AssistantToolError(f"{normalized_item_type} was not found")

    saved_item = SavedItem(
        student_id=student_exists,
        job_id=item_id if normalized_item_type == "job" else None,
        event_id=item_id if normalized_item_type == "event" else None,
    )
    db.add(saved_item)
    db.commit()

    return {
        "saved": True,
        "already_saved": False,
        "item_type": normalized_item_type,
        "item_id": item_id,
    }
