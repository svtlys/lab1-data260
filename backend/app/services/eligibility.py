"""
pure event eligibility checks shared by event workflows.
"""

from datetime import datetime
from typing import Any


def _get(obj: Any, name: str):
    """read a field from either a dictionary or an ORM object."""

    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


def parse_majors(value: str | None) -> list[str]:
    """normalize a comma-separated major list."""

    if not value:
        return []
    return [major.strip().lower() for major in str(value).split(",") if major.strip()]


def check_eligibility(event: Any, student: Any) -> tuple[bool, list[str]]:
    """return whether a student meets every event requirement."""

    reasons = []
    majors = parse_majors(_get(event, "eligible_majors"))
    if majors:
        major = (_get(student, "major") or "").strip().lower()
        if major not in majors:
            reasons.append("Open to these majors only: " + ", ".join(item.title() for item in majors))

    min_cgpa = _get(event, "min_cgpa")
    if min_cgpa is not None:
        cgpa = _get(student, "cgpa")
        if cgpa is None or float(cgpa) < float(min_cgpa):
            reasons.append(f"Requires a CGPA of at least {float(min_cgpa):.2f}")

    year = _get(student, "graduation_year")
    min_year = _get(event, "min_grad_year")
    max_year = _get(event, "max_grad_year")
    if min_year is not None and (year is None or int(year) < int(min_year)):
        reasons.append(f"Requires graduation year {int(min_year)} or later")
    if max_year is not None and (year is None or int(year) > int(max_year)):
        reasons.append(f"Requires graduation year {int(max_year)} or earlier")

    return not reasons, reasons


def check_registration_open(event: Any, registered_count: int, now: datetime | None = None) -> tuple[bool, str | None]:
    """check whether an event is still within its date and capacity limits."""

    current_time = now or datetime.now()
    event_date = _get(event, "event_date")
    if isinstance(event_date, str):
        event_date = datetime.fromisoformat(event_date)
    if event_date is not None and event_date < current_time:
        return False, "This event has already happened"

    capacity = _get(event, "capacity")
    if capacity is not None and registered_count >= int(capacity):
        return False, "This event is full"
    return True, None
