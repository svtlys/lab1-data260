"""assistant service entry point."""

from app.api.routes.assistant import router as assistant_router
from app.service_apps.factory import create_service_app


app = create_service_app(
    "p16-assistant-service",
    [assistant_router],
)
