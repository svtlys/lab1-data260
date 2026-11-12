"""event service entry point."""

from app.api.routes.events import router as event_router
from app.service_apps.factory import create_service_app


app = create_service_app(
    "p16-event-service",
    [event_router],
)
