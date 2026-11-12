"""job service entry point."""

from app.api.routes.jobs import student_jobs_router
from app.service_apps.factory import create_service_app


app = create_service_app(
    "p16-job-service",
    [student_jobs_router],
)
