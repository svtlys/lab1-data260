"""Event eligibility checks (pure functions, no database access).

Used by the company registrations page, the student registration route, and the
assistant's search_events tool, so the rule lives in exactly one place.

An event is open to everyone unless it sets one of:
  eligible_majors  comma-separated list (case-insensitive); NULL/empty = any major
  min_cgpa         student's cgpa must be >= this
  min_grad_year / max_grad_year   inclusive graduation-year window
A missing student value fails a requirement that needs it (we can't prove they qualify).
"""
from datetime import datetime
from typing import Any, List, Optional, Tuple


def _get(obj: Any, name: str):
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


def parse_majors(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [m.strip().lower() for m in str(value).split(",") if m.strip()]


def check_eligibility(event: Any, student: Any) -> Tuple[bool, List[str]]:
    """Return (eligible, reasons). `reasons` lists every unmet requirement."""
    reasons: List[str] = []

    majors = parse_majors(_get(event, "eligible_majors"))
    if majors:
        major = (_get(student, "major") or "").strip().lower()
        if major not in majors:
            reasons.append("Open to these majors only: " + ", ".join(m.title() for m in majors))

    min_cgpa = _get(event, "min_cgpa")
    if min_cgpa is not None:
        cgpa = _get(student, "cgpa")
        if cgpa is None or float(cgpa) < float(min_cgpa):
            reasons.append(f"Requires a CGPA of at least {float(min_cgpa):.2f}")

    year = _get(student, "graduation_year")
    lo, hi = _get(event, "min_grad_year"), _get(event, "max_grad_year")
    if lo is not None and (year is None or int(year) < int(lo)):
        reasons.append(f"Requires graduation year {int(lo)} or later")
    if hi is not None and (year is None or int(year) > int(hi)):
        reasons.append(f"Requires graduation year {int(hi)} or earlier")

    return (not reasons, reasons)


def check_registration_open(event: Any, registered_count: int, now: Optional[datetime] = None) -> Tuple[bool, Optional[str]]:
    """Capacity and date check, separate from who-may-attend."""
    now = now or datetime.now()
    when = _get(event, "event_date")
    if isinstance(when, str):
        when = datetime.fromisoformat(when)
    if when is not None and when < now:
        return False, "This event has already happened"
    cap = _get(event, "capacity")
    if cap is not None and registered_count >= int(cap):
        return False, "This event is full"
    return True, None
