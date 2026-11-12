"""
student application and company applicant routes.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_company, require_student
from app.api.routes.company import find_company_profile
from app.core.config import settings
from app.core.database import get_db
from app.core.mongo import get_mongo_database
from app.messaging.envelope import (
    APPLICATION_CREATED,
    APPLICATION_UPDATED,
    APPLICATION_STATUS_CHANGED,
    create_envelope,
)
from app.messaging.producer import publish_event
from app.models.application import Application
from app.models.job import Job
from app.models.student_profile import StudentProfile
from app.models.user import User
from app.schemas.application import ApplicationResponse, ApplicationStatusUpdateRequest


MAX_RESUME_BYTES = 5 * 1024 * 1024
UPLOAD_DIR = Path(__file__).resolve().parents[3] / "uploads" / "resumes"
logger = logging.getLogger(__name__)

# group student application endpoints under /api/jobs and /api/students
student_router = APIRouter(tags=["applications"])

# group company application endpoints under /api/companies
company_router = APIRouter(
    prefix="/api/companies/me",
    tags=["company applications"],
)


def application_row(application, job, student=None) -> dict:
    """convert joined database objects into a safe response dictionary."""

    return {
        "id": application.id,
        "job_id": application.job_id,
        "student_id": application.student_id,
        "status": application.status,
        "applied_at": application.applied_at,
        "resume_filename": application.resume_filename,
        "job_title": job.title if job else None,
        "company_name": job.company_name if job else None,
        "student_name": student.full_name if student else None,
        "college_name": student.college_name if student else None,
        "major": student.major if student else None,
    }


def mongo_application_row(
    application: dict[str, Any],
    job: dict[str, Any] | None = None,
    student: dict[str, Any] | None = None,
    resume: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """map Mongo application data to the existing response shape."""

    return {
        "id": int(application["id"]),
        "job_id": int(application["job_id"]),
        "student_id": int(application["student_id"]),
        "status": application["status"],
        "applied_at": application["applied_at"],
        "resume_filename": application.get("resume_filename")
        or (resume.get("filename") if resume else None),
        "job_title": job.get("title") if job else None,
        "company_name": job.get("company_name") if job else None,
        "student_name": student.get("full_name") if student else None,
        "college_name": student.get("college_name") if student else None,
        "major": student.get("major") if student else None,
    }


def _get_mongo_application_database() -> Any | None:
    """return Mongo for application reads without leaking connection errors."""

    try:
        return get_mongo_database()
    except Exception:
        return None


def _mongo_resume(database: Any, application_id: int) -> dict[str, Any] | None:
    """look up resume metadata without returning stored file paths."""

    return database["resumes"].find_one({"application_id": application_id})


def _get_my_applications_from_mongo(
    user_id: int,
) -> tuple[bool, list[dict[str, Any]] | None]:
    """read a student's applications from Mongo or signal SQL fallback."""

    database = _get_mongo_application_database()
    if database is None:
        return False, None
    try:
        student = database["student_profiles"].find_one({"user_id": user_id})
        if student is None:
            return True, None
        applications = database["applications"].find(
            {"student_id": student["id"]}
        ).sort("applied_at", -1)
        rows = []
        for application in applications:
            job = database["jobs"].find_one({"id": application["job_id"]})
            if job is None:
                continue
            rows.append(
                mongo_application_row(
                    application,
                    job=job,
                    student=student,
                    resume=_mongo_resume(database, int(application["id"])),
                )
            )
        return True, rows
    except Exception:
        return False, None


def _get_job_applications_from_mongo(
    user_id: int,
    job_id: int,
) -> tuple[bool, list[dict[str, Any]] | None, str | None]:
    """read company applicants after checking company job ownership."""

    database = _get_mongo_application_database()
    if database is None:
        return False, None, None
    try:
        company = database["company_profiles"].find_one({"user_id": user_id})
        if company is None:
            return True, None, "company profile was not found"
        job = database["jobs"].find_one(
            {"id": job_id, "company_id": company["id"]}
        )
        if job is None:
            return True, None, "job was not found"
        applications = database["applications"].find(
            {"job_id": job_id}
        ).sort("applied_at", 1)
        rows = []
        for application in applications:
            student = database["student_profiles"].find_one(
                {"id": application["student_id"]}
            )
            if student is None:
                continue
            rows.append(
                mongo_application_row(
                    application,
                    job=job,
                    student=student,
                    resume=_mongo_resume(database, int(application["id"])),
                )
            )
        return True, rows, None
    except Exception:
        return False, None, None


def _get_resume_from_mongo(
    user_id: int,
    application_id: int,
) -> tuple[bool, dict[str, Any] | None, str | None]:
    """read one company-owned resume from Mongo without exposing paths."""

    database = _get_mongo_application_database()
    if database is None:
        return False, None, None
    try:
        company = database["company_profiles"].find_one({"user_id": user_id})
        if company is None:
            return True, None, "company profile was not found"
        application = database["applications"].find_one({"id": application_id})
        if application is None:
            return True, None, "resume was not found"
        job = database["jobs"].find_one(
            {"id": application["job_id"], "company_id": company["id"]}
        )
        if job is None:
            return True, None, "resume was not found"
        resume = _mongo_resume(database, application_id)
        if resume is None or not resume.get("content"):
            return True, None, "resume was not found"
        return True, resume, None
    except Exception:
        return False, None, None


async def read_pdf_resume(resume: UploadFile | None) -> tuple[str | None, str | None]:
    """validate and store an optional PDF resume outside tracked source files."""

    if resume is None:
        return None, None

    filename = resume.filename or "resume.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="resume must be a PDF file",
        )
    if resume.content_type not in {None, "application/pdf"}:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="resume must be a PDF file",
        )

    content = await resume.read(MAX_RESUME_BYTES + 1)
    if len(content) > MAX_RESUME_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="resume must be 5 MB or smaller",
        )
    if not content.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="resume must contain a valid PDF header",
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid4().hex}.pdf"
    stored_path = UPLOAD_DIR / stored_name
    stored_path.write_bytes(content)
    return filename, str(stored_path)


@student_router.post(
    "/api/jobs/{job_id}/applications",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def apply_to_job(
    job_id: int,
    request: Request,
    resume: UploadFile | None = File(default=None),
    current_user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    """create one application for the logged-in student."""

    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="job was not found",
        )

    student = db.scalar(
        select(StudentProfile).where(StudentProfile.user_id == current_user.id)
    )
    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="student profile was not found",
        )

    existing = db.scalar(
        select(Application).where(
            Application.job_id == job.id,
            Application.student_id == student.id,
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="you already applied to this job",
        )

    resume_filename, resume_path = await read_pdf_resume(resume)
    application = Application(
        job_id=job.id,
        student_id=student.id,
        resume_filename=resume_filename,
        resume_path=resume_path,
    )
    db.add(application)
    try:
        db.commit()
        db.refresh(application)
    except Exception:
        db.rollback()
        if resume_path:
            Path(resume_path).unlink(missing_ok=True)
        raise

    response = application_row(application, job, student)
    if settings.kafka_enabled:
        try:
            trace_id = request.headers.get("X-Trace-Id")
            payload = {
                "application_id": application.id,
                "job_id": application.job_id,
                "student_id": application.student_id,
                "status": application.status,
            }
            if application.resume_filename:
                payload["resume_filename"] = application.resume_filename
            envelope = create_envelope(
                APPLICATION_CREATED,
                payload,
                {
                    "user_id": current_user.id,
                    "role": current_user.role.value,
                },
                trace_id=trace_id,
            )
            publish_event(envelope, "application.created", application.id)
        except Exception:
            logger.error(
                "application.created event was not published; committed MySQL application remains"
            )
    return response


@student_router.get(
    "/api/students/me/applications",
    response_model=list[ApplicationResponse],
)
def get_my_applications(
    current_user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    """return only applications owned by the logged-in student."""

    mongo_available, mongo_rows = _get_my_applications_from_mongo(current_user.id)
    if mongo_available:
        if mongo_rows is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="student profile was not found",
            )
        return mongo_rows

    student = db.scalar(
        select(StudentProfile).where(StudentProfile.user_id == current_user.id)
    )
    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="student profile was not found",
        )

    rows = db.execute(
        select(Application, Job)
        .join(Job, Job.id == Application.job_id)
        .where(Application.student_id == student.id)
        .order_by(Application.applied_at.desc())
    ).all()
    return [application_row(application, job, student) for application, job in rows]


@company_router.get(
    "/jobs/{job_id}/applications",
    response_model=list[ApplicationResponse],
)
def get_job_applications(
    job_id: int,
    current_user: User = Depends(require_company),
    db: Session = Depends(get_db),
):
    """return applicants only for a job owned by the company."""

    mongo_available, mongo_rows, mongo_error = _get_job_applications_from_mongo(
        current_user.id,
        job_id,
    )
    if mongo_available:
        if mongo_rows is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=mongo_error or "job was not found",
            )
        return mongo_rows

    company = find_company_profile(current_user, db)
    job = db.scalar(
        select(Job).where(Job.id == job_id, Job.company_id == company.id)
    )
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="job was not found",
        )

    rows = db.execute(
        select(Application, StudentProfile)
        .join(StudentProfile, StudentProfile.id == Application.student_id)
        .where(Application.job_id == job.id)
        .order_by(Application.applied_at.asc())
    ).all()
    return [application_row(application, job, student) for application, student in rows]


def _update_application_status(
    application_id: int,
    request: ApplicationStatusUpdateRequest,
    current_user: User = Depends(require_company),
    db: Session = Depends(get_db),
    http_request: Request | None = None,
):
    """update status only for an application on the company's job."""

    company = find_company_profile(current_user, db)
    row = db.execute(
        select(Application, Job, StudentProfile)
        .join(Job, Job.id == Application.job_id)
        .join(StudentProfile, StudentProfile.id == Application.student_id)
        .where(
            Application.id == application_id,
            Job.company_id == company.id,
        )
    ).first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="application was not found",
        )

    application, job, student = row
    previous_status = application.status
    application.status = request.status
    db.commit()
    db.refresh(application)
    response = application_row(application, job, student)
    if settings.kafka_enabled:
        trace_id = (
            http_request.headers.get("X-Trace-Id")
            if http_request
            else None
        ) or str(uuid4())
        updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        payload = {
            "application_id": application.id,
            "job_id": application.job_id,
            "student_id": application.student_id,
            "previous_status": previous_status,
            "new_status": application.status,
            "updated_at": updated_at,
        }
        actor = {
            "user_id": current_user.id,
            "role": current_user.role.value,
        }
        for event_type, topic_suffix in (
            (APPLICATION_UPDATED, "application.updated"),
            (APPLICATION_STATUS_CHANGED, "application.status_changed"),
        ):
            try:
                envelope = create_envelope(
                    event_type,
                    payload,
                    actor,
                    trace_id=trace_id,
                )
                publish_event(envelope, topic_suffix, application.id)
            except Exception:
                logger.error(
                    "application status event was not published; committed MySQL update remains"
                )
    return response


@company_router.patch(
    "/applications/{application_id}/status",
    response_model=ApplicationResponse,
)
def update_application_status(
    application_id: int,
    request: ApplicationStatusUpdateRequest,
    current_user: User = Depends(require_company),
    db: Session = Depends(get_db),
    http_request: Request = None,
):
    """update an application through the required patch route."""

    return _update_application_status(
        application_id,
        request,
        current_user,
        db,
        http_request,
    )


@company_router.put(
    "/applications/{application_id}/status",
    response_model=ApplicationResponse,
)
def update_application_status_legacy(
    application_id: int,
    request: ApplicationStatusUpdateRequest,
    current_user: User = Depends(require_company),
    db: Session = Depends(get_db),
    http_request: Request = None,
):
    """support the integrated frontend's existing put request."""

    return _update_application_status(
        application_id,
        request,
        current_user,
        db,
        http_request,
    )


@company_router.get(
    "/applications/{application_id}/resume",
)
def get_application_resume(
    application_id: int,
    current_user: User = Depends(require_company),
    db: Session = Depends(get_db),
):
    """return a PDF resume only to the job-owning company."""

    mongo_available, mongo_resume, mongo_error = _get_resume_from_mongo(
        current_user.id,
        application_id,
    )
    if mongo_available:
        if mongo_resume is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=mongo_error or "resume was not found",
            )
        filename = Path(str(mongo_resume.get("filename") or "resume.pdf")).name
        return Response(
            content=mongo_resume["content"],
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    company = find_company_profile(current_user, db)
    row = db.execute(
        select(Application, Job)
        .join(Job, Job.id == Application.job_id)
        .where(
            Application.id == application_id,
            Job.company_id == company.id,
        )
    ).first()
    if row is None or row[0].resume_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="resume was not found",
        )

    path = Path(row[0].resume_path)
    if not path.is_file() or path.parent != UPLOAD_DIR:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="resume was not found",
        )
    return FileResponse(path, media_type="application/pdf", filename=row[0].resume_filename)
