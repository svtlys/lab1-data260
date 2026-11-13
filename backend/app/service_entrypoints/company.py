"""company service entry point."""

from app.api.routes.company import router as company_profile_router
from app.api.routes.company_events import router as company_events_router
from app.api.routes.jobs import company_jobs_router
from app.api.routes.student_profile import company_student_router
from app.service_apps.factory import create_service_app


app = create_service_app(
    "p16-company-service",
    [
        company_profile_router,
        company_jobs_router,
        company_events_router,
        company_student_router,
    ],
)
