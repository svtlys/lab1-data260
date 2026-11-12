"""application service entry point."""

from fastapi import APIRouter

from app.api.routes.applications import (
    company_router as company_applications_router,
    student_router as student_applications_router,
)
from app.service_apps.factory import create_service_app


applications_router = APIRouter()
applications_router.include_router(company_applications_router)
applications_router.include_router(student_applications_router)


app = create_service_app(
    "p16-application-service",
    [applications_router],
)
