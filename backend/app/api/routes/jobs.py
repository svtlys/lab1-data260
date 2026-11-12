"""
student job browsing and company job posting routes.
"""

import logging
import re
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from bson.decimal128 import Decimal128
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import require_company, require_student
from app.api.routes.company import find_company_profile
from app.core.config import settings
from app.core.database import get_db
from app.core.mongo import get_mongo_database
from app.messaging.envelope import JOB_CREATED, create_envelope
from app.messaging.producer import publish_event
from app.models.application import Application
from app.models.job import Job
from app.models.user import User
from app.schemas.job import EmploymentType, JobCreateRequest, JobResponse


logger = logging.getLogger(__name__)


LEGACY_EMPLOYMENT_TYPE_MAP = {
    "internship": "Internship",
    "full-time": "Full-time",
    "part-time": "Part-time",
    "on-campus": "On-campus",
}


# group student job endpoints under /api/jobs
student_router = APIRouter(
    prefix="/api/jobs",
    tags=["jobs"],
)

# group company-owned job endpoints under /api/companies
company_router = APIRouter(
    prefix="/api/companies/me/jobs",
    tags=["company jobs"],
)


def job_response(job: Job, db: Session) -> dict:
    """add applicant counts without exposing application records."""

    applicant_count = db.scalar(
        select(func.count(Application.id)).where(Application.job_id == job.id)
    ) or 0
    pending_count = db.scalar(
        select(func.count(Application.id)).where(
            Application.job_id == job.id,
            Application.status == "Pending",
        )
    ) or 0
    employment_type = normalize_employment_type(job.employment_type)
    return {
        "id": job.id,
        "company_id": job.company_id,
        "title": job.title,
        "description": job.description,
        "company_name": job.company_name,
        "location": job.location,
        "city": job.city,
        "employment_type": employment_type,
        "is_remote": job.is_remote,
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "required_skills": job.required_skills,
        "posted_at": job.posted_at,
        "deadline": job.deadline,
        "applicant_count": int(applicant_count),
        "pending_count": int(pending_count),
    }


def normalize_employment_type(value: str) -> str:
    """normalize only the legacy employment values supported by Lab 1."""

    return LEGACY_EMPLOYMENT_TYPE_MAP.get(value, value)


def _mongo_value(value: Any, field_name: str) -> Any:
    """convert Mongo scalar values to the existing response types."""

    if isinstance(value, Decimal128):
        return value.to_decimal()
    if field_name == "deadline" and isinstance(value, datetime):
        return value.date()
    if isinstance(value, Decimal):
        return value
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    return value


def mongo_job_response(job: dict[str, Any], database: Any) -> dict[str, Any]:
    """map one Mongo job document to the existing Lab 1 response shape."""

    job_id = int(job["id"])
    applicant_count = database["applications"].count_documents({"job_id": job_id})
    pending_count = database["applications"].count_documents(
        {"job_id": job_id, "status": "Pending"}
    )
    return {
        "id": job_id,
        "company_id": job.get("company_id"),
        "title": job["title"],
        "description": job["description"],
        "company_name": job["company_name"],
        "location": job["location"],
        "city": job["city"],
        "employment_type": normalize_employment_type(job["employment_type"]),
        "is_remote": job["is_remote"],
        "salary_min": _mongo_value(job.get("salary_min"), "salary_min"),
        "salary_max": _mongo_value(job.get("salary_max"), "salary_max"),
        "required_skills": job.get("required_skills"),
        "posted_at": _mongo_value(job["posted_at"], "posted_at"),
        "deadline": _mongo_value(job.get("deadline"), "deadline"),
        "applicant_count": int(applicant_count),
        "pending_count": int(pending_count),
    }


def _mongo_employment_values(employment_type: EmploymentType) -> list[str]:
    """match canonical and migrated lowercase employment values."""

    return [employment_type, employment_type.lower()]


def _search_jobs_from_mongo(
    search: str | None,
    city: str | None,
    employment_type: EmploymentType | None,
    is_remote: bool | None,
) -> list[dict[str, Any]] | None:
    """read student jobs from Mongo or return none when fallback is required."""

    try:
        database = get_mongo_database()
        if database is None:
            return None

        filters: dict[str, Any] = {}
        if search:
            filters["$or"] = [
                {field: {"$regex": re.escape(search), "$options": "i"}}
                for field in (
                    "title",
                    "description",
                    "company_name",
                    "required_skills",
                )
            ]
        if city:
            filters["city"] = city
        if employment_type:
            filters["employment_type"] = {
                "$in": _mongo_employment_values(employment_type)
            }
        if is_remote is not None:
            filters["is_remote"] = is_remote

        cursor = database["jobs"].find(filters).sort("posted_at", -1)
        return [mongo_job_response(job, database) for job in cursor]
    except Exception:
        return None


def _get_job_from_mongo(job_id: int) -> tuple[bool, dict[str, Any] | None]:
    """return availability and one Mongo job without exposing Mongo errors."""

    try:
        database = get_mongo_database()
        if database is None:
            return False, None
        job = database["jobs"].find_one({"id": job_id})
        if job is None:
            return True, None
        return True, mongo_job_response(job, database)
    except Exception:
        return False, None


@company_router.post(
    "",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_job(
    request: JobCreateRequest,
    current_user: User = Depends(require_company),
    db: Session = Depends(get_db),
    http_request: Request = None,
):
    """create a job owned by the logged-in company."""

    company_profile = find_company_profile(current_user, db)
    job = Job(
        company_id=company_profile.id,
        title=request.title,
        description=request.description,
        company_name=company_profile.company_name,
        location=f"{request.city}, CA",
        city=request.city,
        employment_type=request.employment_type,
        is_remote=request.is_remote,
        salary_min=request.salary_min,
        salary_max=request.salary_max,
        required_skills=request.required_skills,
        posted_at=datetime.now(timezone.utc).replace(tzinfo=None),
        deadline=request.deadline,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    if settings.kafka_enabled:
        try:
            posted_at = job.posted_at
            if posted_at.tzinfo is None:
                posted_at = posted_at.replace(tzinfo=timezone.utc)
            posted_at = posted_at.astimezone(timezone.utc)
            trace_id = http_request.headers.get("X-Trace-Id") if http_request else None
            envelope = create_envelope(
                JOB_CREATED,
                {
                    "job_id": job.id,
                    "company_id": job.company_id,
                    "title": job.title,
                    "city": job.city,
                    "employment_type": job.employment_type,
                    "is_remote": job.is_remote,
                    "posted_at": posted_at.isoformat().replace("+00:00", "Z"),
                },
                {
                    "user_id": current_user.id,
                    "role": current_user.role.value,
                },
                trace_id=trace_id,
            )
            publish_event(envelope, "job.created", job.id)
        except Exception:
            logger.error(
                "job.created event was not published; committed MySQL job remains"
            )

    return job_response(job, db)


@company_router.get(
    "",
    response_model=list[JobResponse],
)
def get_my_jobs(
    current_user: User = Depends(require_company),
    db: Session = Depends(get_db),
):
    """return only jobs owned by the logged-in company."""

    company_profile = find_company_profile(current_user, db)
    statement = (
        select(Job)
        .where(Job.company_id == company_profile.id)
        .order_by(Job.id.desc())
    )

    return [job_response(job, db) for job in db.scalars(statement).all()]


@student_router.get(
    "",
    response_model=list[JobResponse],
)
def search_jobs(
    search: str | None = Query(default=None, max_length=100),
    city: str | None = Query(default=None, max_length=100),
    employment_type: EmploymentType | None = Query(default=None),
    is_remote: bool | None = None,
    current_user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    """search all job postings as a logged-in student."""

    mongo_jobs = _search_jobs_from_mongo(search, city, employment_type, is_remote)
    if mongo_jobs is not None:
        return mongo_jobs

    statement = select(Job)

    if search:
        search_pattern = f"%{search}%"
        statement = statement.where(
            Job.title.like(search_pattern)
            | Job.description.like(search_pattern)
            | Job.company_name.like(search_pattern)
            | Job.required_skills.like(search_pattern)
        )
    if city:
        statement = statement.where(Job.city == city)
    if employment_type:
        statement = statement.where(Job.employment_type == employment_type)
    if is_remote is not None:
        statement = statement.where(Job.is_remote == is_remote)

    statement = statement.order_by(Job.posted_at.desc())
    return [job_response(job, db) for job in db.scalars(statement).all()]


@student_router.get(
    "/{job_id}",
    response_model=JobResponse,
)
def get_job_details(
    job_id: int,
    current_user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    """return one job posting to a logged-in student."""

    mongo_available, mongo_job = _get_job_from_mongo(job_id)
    if mongo_available:
        if mongo_job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="job was not found",
            )
        return mongo_job

    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="job was not found",
        )
    return job_response(job, db)
