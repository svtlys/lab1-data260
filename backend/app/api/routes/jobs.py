"""
student job browsing and company job posting routes.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import require_company, require_student
from app.api.routes.company import find_company_profile
from app.core.database import get_db
from app.models.application import Application
from app.models.job import Job
from app.models.user import User
from app.schemas.job import JobCreateRequest, JobResponse


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
    return {
        "id": job.id,
        "company_id": job.company_id,
        "title": job.title,
        "description": job.description,
        "company_name": job.company_name,
        "location": job.location,
        "city": job.city,
        "employment_type": job.employment_type,
        "is_remote": job.is_remote,
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "required_skills": job.required_skills,
        "posted_at": job.posted_at,
        "deadline": job.deadline,
        "applicant_count": int(applicant_count),
        "pending_count": int(pending_count),
    }


@company_router.post(
    "",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_job(
    request: JobCreateRequest,
    current_user: User = Depends(require_company),
    db: Session = Depends(get_db),
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
    employment_type: str | None = Query(default=None, max_length=100),
    is_remote: bool | None = None,
    current_user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    """search all job postings as a logged-in student."""

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

    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="job was not found",
        )
    return job_response(job, db)
