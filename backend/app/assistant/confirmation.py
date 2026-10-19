"""
confirmation rules for assistant actions that change student data.
"""

from typing import Any


READ_ONLY_TOOLS = frozenset(
    {
        "get_student_preferences",
        "search_jobs",
        "get_job_details",
        "search_events",
    }
)
SAVE_TOOL_NAME = "save_job_or_event"


def confirm_action(
    tool_name: str,
    arguments: dict[str, Any],
    auto_approve: bool = False,
) -> str:
    """approve read-only tools and require explicit approval for saves."""

    # read-only tools do not change student data
    if tool_name in READ_ONLY_TOOLS:
        return "approved"

    if tool_name != SAVE_TOOL_NAME:
        return "error: confirmation is not configured for this tool"

    if auto_approve:
        return "approved"

    return (
        "cancelled: the job or event was not saved because explicit student "
        "confirmation was declined"
    )
