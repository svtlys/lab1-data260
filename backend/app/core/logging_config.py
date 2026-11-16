"""
log setup shared by the API apps and the Kafka workers.

without this, Python drops every INFO message from our own loggers (only warnings reach the
console), so the trace_id lines the assistant, the Kafka consumer and the workers write were never
visible. every service calls configure_logging() once at start-up; LOG_LEVEL changes the level.
"""

from __future__ import annotations

import logging
import os

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
_configured = False


def configure_logging() -> None:
    """send app.* logs (INFO by default) to the console in one line each; safe to call twice."""
    global _configured
    if _configured:
        return
    level = getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    app_logger = logging.getLogger("app")
    app_logger.setLevel(level)
    if not app_logger.handlers:
        app_logger.addHandler(handler)
    _configured = True
