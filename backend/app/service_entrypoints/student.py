"""student service entry point."""

from app.api.routes.auth import router as auth_router
from app.api.routes.student_profile import student_profile_router
from app.service_apps.factory import create_service_app


app = create_service_app(
    "p16-student-service",
    [auth_router, student_profile_router],
)
