"""
request and response schemas for the hand-built assistant.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AssistantChatRequest(BaseModel):
    """validate one assistant chat request."""

    message: str = Field(min_length=1, max_length=4000)
    conversation_id: int | None = Field(default=None, ge=1)
    confirm_save: bool = Field(
        default=False,
        description="explicitly approve a save_job_or_event call for this turn",
    )


class AssistantToolCallResponse(BaseModel):
    """return one tool-call record to the frontend."""

    iteration: int
    tool_call_id: str
    tool_name: str
    arguments: Any
    result: Any | None = None
    error: str | None = None


class AssistantChatResponse(BaseModel):
    """return the assistant answer and trace metadata."""

    conversation_id: int
    answer: str
    iterations: int
    tool_call_count: int
    repair_attempts: int
    failure_mode: str | None = None
    reached_iteration_ceiling: bool
    tool_calls: list[AssistantToolCallResponse]
    created_at: datetime
