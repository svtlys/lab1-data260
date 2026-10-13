"""
manual assistant loop for Ollama tool calling.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.assistant.tools import (
    AssistantToolError,
    get_job_details,
    get_student_preferences,
    save_job_or_event,
    search_events,
    search_jobs,
)
from app.services.ollama_client import OllamaClient


DEFAULT_MAX_ITERATIONS = 5

SYSTEM_PROMPT = """
you are a helpful student career assistant for the pair 16 handshake platform.
use the available tools when the student asks about preferences, jobs, events,
or saving an opportunity. do not invent database results. after using a tool,
explain the result in clear beginner-friendly language.
""".strip()


TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_student_preferences",
            "description": "get the logged-in student's profile preferences",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_jobs",
            "description": "search jobs using optional filters",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "city": {"type": "string"},
                    "employment_type": {"type": "string"},
                    "is_remote": {"type": "boolean"},
                    "required_skill": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 50},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_job_details",
            "description": "get full details for one job by ID",
            "parameters": {
                "type": "object",
                "properties": {"job_id": {"type": "integer"}},
                "required": ["job_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_events",
            "description": "search events using optional filters",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "city": {"type": "string"},
                    "event_type": {"type": "string"},
                    "is_virtual": {"type": "boolean"},
                    "start_date": {"type": "string"},
                    "end_date": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 50},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_job_or_event",
            "description": "save one job or event for the logged-in student",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_type": {"type": "string", "enum": ["job", "event"]},
                    "item_id": {"type": "integer"},
                },
                "required": ["item_type", "item_id"],
            },
        },
    },
]


@dataclass
class AssistantRunResult:
    """contain the assistant answer and trace information."""

    answer: str
    messages: list[dict[str, Any]]
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    iterations: int = 0
    reached_iteration_ceiling: bool = False


class AssistantLoop:
    """coordinate Ollama responses and manual database tools."""

    def __init__(
        self,
        client: OllamaClient | None = None,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
    ):
        # keep the ceiling explicit so runaway tool calls cannot continue
        if max_iterations < 1:
            raise ValueError("max_iterations must be at least 1")

        self.client = client or OllamaClient()
        self.max_iterations = max_iterations

    def _tool_functions(self, db: Session, student_id: int) -> dict[str, Callable[..., Any]]:
        """bind the current database and student to each tool."""

        return {
            "get_student_preferences": lambda **arguments: get_student_preferences(
                db,
                student_id,
                **arguments,
            ),
            "search_jobs": lambda **arguments: search_jobs(db, **arguments),
            "get_job_details": lambda **arguments: get_job_details(db, **arguments),
            "search_events": lambda **arguments: search_events(db, **arguments),
            "save_job_or_event": lambda **arguments: save_job_or_event(
                db,
                student_id,
                **arguments,
            ),
        }

    @staticmethod
    def _tool_arguments(raw_arguments: Any) -> dict[str, Any]:
        """normalize Ollama tool arguments into a dictionary."""

        if raw_arguments is None:
            return {}

        if isinstance(raw_arguments, dict):
            return raw_arguments

        if isinstance(raw_arguments, str):
            try:
                parsed_arguments = json.loads(raw_arguments)
            except json.JSONDecodeError as error:
                raise AssistantToolError("tool arguments were not valid JSON") from error

            if isinstance(parsed_arguments, dict):
                return parsed_arguments

        raise AssistantToolError("tool arguments must be a JSON object")

    def run(
        self,
        db: Session,
        student_id: int,
        user_message: str,
        history: list[dict[str, Any]] | None = None,
    ) -> AssistantRunResult:
        """run one bounded conversation through Ollama and the manual tools."""

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        tool_functions = self._tool_functions(db, student_id)
        tool_call_log: list[dict[str, Any]] = []

        for iteration in range(1, self.max_iterations + 1):
            response = self.client.chat(
                messages,
                tools=TOOL_DEFINITIONS,
            )
            response_message = response.get("message", {})
            if not isinstance(response_message, dict):
                response_message = {}

            assistant_message = {
                "role": "assistant",
                "content": response_message.get("content") or "",
            }
            tool_calls = response_message.get("tool_calls") or []
            if tool_calls:
                assistant_message["tool_calls"] = tool_calls
            messages.append(assistant_message)

            if not tool_calls:
                return AssistantRunResult(
                    answer=assistant_message["content"],
                    messages=messages,
                    tool_calls=tool_call_log,
                    iterations=iteration,
                )

            for tool_call in tool_calls:
                function_data = tool_call.get("function", {})
                tool_name = function_data.get("name", "")
                tool_call_id = tool_call.get("id", f"tool-{iteration}")
                raw_arguments = function_data.get("arguments", {})
                log_entry: dict[str, Any] = {
                    "iteration": iteration,
                    "tool_call_id": tool_call_id,
                    "tool_name": tool_name,
                    "arguments": raw_arguments,
                }

                try:
                    arguments = self._tool_arguments(raw_arguments)
                    tool_function = tool_functions.get(tool_name)
                    if tool_function is None:
                        raise AssistantToolError(f"unknown assistant tool: {tool_name}")

                    tool_result = tool_function(**arguments)
                    log_entry["result"] = tool_result
                except (AssistantToolError, TypeError, ValueError) as error:
                    tool_result = {"error": str(error)}
                    log_entry["error"] = str(error)

                tool_call_log.append(log_entry)
                messages.append(
                    {
                        "role": "tool",
                        "tool_name": tool_name,
                        "tool_call_id": tool_call_id,
                        "content": json.dumps(tool_result, default=str),
                    }
                )

        return AssistantRunResult(
            answer=(
                "I reached the assistant's tool-call limit before completing "
                "the request. Please try a more specific question."
            ),
            messages=messages,
            tool_calls=tool_call_log,
            iterations=self.max_iterations,
            reached_iteration_ceiling=True,
        )
