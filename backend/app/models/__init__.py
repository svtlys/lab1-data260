"""
make all database models available from one package.
"""

from app.models.company_profile import CompanyProfile
from app.models.assistant_conversation import AssistantConversation, AssistantMessage
from app.models.assistant_tool_log import AssistantToolLog
from app.models.event import Event
from app.models.event_registration import EventRegistration
from app.models.job import Job
from app.models.saved_item import SavedItem
from app.models.student_profile import StudentProfile
from app.models.user import User, UserRole

__all__ = [
    "CompanyProfile",
    "AssistantConversation",
    "AssistantMessage",
    "AssistantToolLog",
    "Event",
    "EventRegistration",
    "Job",
    "SavedItem",
    "StudentProfile",
    "User",
    "UserRole",
]
