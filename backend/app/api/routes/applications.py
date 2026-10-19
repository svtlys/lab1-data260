"""
student application and company applicant routes.
"""

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_company, require_student
from app.api.routes.company import find_company_profile
from app.core.database import get_db
from app.models.application import Application
from app.models.job import Job
from app.models.student_profile import StudentProfile
from app.models.user import User
from app.schemas.application import ApplicationResponse, ApplicationStatusUpdateRequest


MAX_RESUME_BYTES = 5 * 1024 * 1024
UPLOAD_DIR = Path(__file__).resolve().parents[3] / "uploads" / "resumes"

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

    return application_row(application, job, student)


@student_router.get(
    "/api/students/me/applications",
    response_model=list[ApplicationResponse],
)
def get_my_applications(
    current_user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    """return only applications owned by the logged-in student."""

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
    application.status = request.status
    db.commit()
    db.refresh(application)
    return application_row(application, job, student)


@company_router.patch(
    "/applications/{application_id}/status",
    response_model=ApplicationResponse,
)
def update_application_status(
    application_id: int,
    request: ApplicationStatusUpdateRequest,
    current_user: User = Depends(require_company),
    db: Session = Depends(get_db),
):
    """update an application through the required patch route."""

    return _update_application_status(application_id, request, current_user, db)


@company_router.put(
    "/applications/{application_id}/status",
    response_model=ApplicationResponse,
)
def update_application_status_legacy(
    application_id: int,
    request: ApplicationStatusUpdateRequest,
    current_user: User = Depends(require_company),
    db: Session = Depends(get_db),
):
    """support the integrated frontend's existing put request."""

    return _update_application_status(application_id, request, current_user, db)


@company_router.get(
    "/applications/{application_id}/resume",
)
def get_application_resume(
    application_id: int,
    current_user: User = Depends(require_company),
    db: Session = Depends(get_db),
):
    """return a PDF resume only to the job-owning company."""

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
