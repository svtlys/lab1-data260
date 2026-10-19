"""
run a deterministic, database-free reliability experiment for the assistant.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path
import sys
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

# allow direct execution from the backend/scripts folder
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.assistant.loop import AssistantLoop
from app.core.database import Base
from app.models.job import Job
from app.models.student_profile import StudentProfile
from app.models.user import User, UserRole
from app.services import ollama_client
from app.assistant import loop as loop_module


SCENARIO_MODES = (
    ["valid"] * 8
    + ["malformed"] * 3
    + ["unknown"] * 2
    + ["text"] * 2
    + ["lost_chain"] * 2
    + ["ollama"]
    + ["database"]
    + ["ceiling"]
)

CATEGORY_ORDER = (
    "valid and correct tool calls",
    "malformed arguments",
    "unknown tool names",
    "text responses when a tool call was required",
    "lost multi-step chains",
    "ollama errors",
    "database errors",
    "iteration-ceiling events",
)


class ScenarioClient:
    """return deterministic responses for one reliability scenario."""

    def __init__(self, mode: str):
        self.mode = mode
        self.calls = 0

    def _tool_response(self, name: str, arguments: Any) -> dict[str, Any]:
        return {
            "message": {
                "content": "",
                "tool_calls": [
                    {
                        "id": f"{self.mode}-{self.calls}",
                        "function": {"name": name, "arguments": arguments},
                    }
                ],
            }
        }

    def complete(self, messages, tools=None):
        self.calls += 1

        if self.mode == "ollama":
            raise ollama_client.OllamaError("simulated Ollama timeout")

        if self.mode == "ceiling":
            return self._tool_response("search_jobs", {"city": "Sunnyvale"})

        repair_requested = any(
            message.get("role") == "system"
            and "repair request:" in message.get("content", "")
            for message in messages
        )

        if self.mode == "text":
            return {"message": {"content": "Here is a result without using a tool."}}

        if self.mode == "lost_chain":
            if self.calls == 1:
                return self._tool_response("get_student_preferences", {})
            return {"message": {"content": "I stopped before searching for jobs."}}

        if self.mode == "malformed" and self.calls == 1:
            return self._tool_response("search_jobs", "not valid json")

        if self.mode == "unknown" and self.calls == 1:
            return self._tool_response("unknown_tool", {})

        if self.mode == "database" and self.calls == 1:
            return self._tool_response("search_jobs", {"city": "Sunnyvale"})

        if self.mode in {"malformed", "unknown", "database"}:
            if repair_requested:
                if self.calls == 2:
                    return self._tool_response("search_jobs", {"city": "Sunnyvale"})
                return {"message": {"content": "I recovered from the tool error."}}
            return {"message": {"content": "I could not recover from the tool error."}}

        if self.mode == "valid":
            if self.calls == 1:
                return self._tool_response("search_jobs", {"city": "Sunnyvale"})
            return {"message": {"content": "I found the requested job."}}

        raise AssertionError(f"unsupported reliability mode: {self.mode}")


def _make_database() -> tuple[Any, Session, User]:
    """create the isolated records used by every experiment turn."""

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = Session(engine)
    user = User(
        role=UserRole.STUDENT,
        email="reliability-experiment@example.com",
        password_hash="test-hash",
    )
    student = StudentProfile(
        user=user,
        full_name="Reliability Experiment Student",
        college_name="Test College",
        city="Sunnyvale",
        major="Computer Science",
    )
    job = Job(
        title="Reliability Python Internship",
        description="A deterministic test job.",
        company_name="Reliability Labs",
        location="Sunnyvale office",
        city="Sunnyvale",
        employment_type="internship",
        is_remote=False,
        required_skills="Python",
        posted_at=datetime(2026, 10, 1, 9, 0),
    )
    db.add_all([user, student, job])
    db.commit()
    db.refresh(user)
    return engine, db, user


def _run_one(mode: str, max_repair_attempts: int) -> dict[str, Any]:
    """run one scenario and return its observable reliability metadata."""

    engine, db, user = _make_database()
    client = ScenarioClient(mode)
    original_search = loop_module.search_jobs
    loop = AssistantLoop(
        client=client,
        max_iterations=5,
        max_repair_attempts=max_repair_attempts,
    )

    def database_failure(db_session, **arguments):
        # return one recoverable database error before the repair path runs
        if not getattr(database_failure, "failed", False):
            database_failure.failed = True
            return "error: simulated database error"
        return original_search(db_session, **arguments)

    if mode == "database":
        loop_module.search_jobs = database_failure
        try:
            result = loop.run(db, user.id, "find a Sunnyvale job")
        finally:
            loop_module.search_jobs = original_search
    else:
        result = loop.run(db, user.id, "run the reliability scenario")

    db.close()
    engine.dispose()
    return {
        "mode": mode,
        "result": result,
        "client_calls": client.calls,
    }


def _category(mode: str, result) -> str:
    """classify one deterministic run for the report."""

    if result.failure_mode == "ollama_error":
        return "ollama errors"
    if result.failure_mode == "iteration_ceiling":
        return "iteration-ceiling events"
    if mode == "valid":
        return "valid and correct tool calls"
    if mode == "text":
        return "text responses when a tool call was required"
    if mode == "lost_chain":
        return "lost multi-step chains"
    if result.repair_succeeded:
        return "valid and correct tool calls"
    if mode == "malformed":
        return "malformed arguments"
    if mode == "unknown":
        return "unknown tool names"
    if mode == "database":
        return "database errors"
    raise AssertionError(f"unclassified reliability mode: {mode}")


def run_experiment() -> dict[str, Counter]:
    """run all 20 turns before and after the one-attempt repair path."""

    before = Counter()
    after = Counter()
    for mode in SCENARIO_MODES:
        before_result = _run_one(mode, max_repair_attempts=0)["result"]
        after_result = _run_one(mode, max_repair_attempts=1)["result"]
        before[_category(mode, before_result)] += 1
        after[_category(mode, after_result)] += 1
    return {"before": before, "after": after}


def main() -> None:
    results = run_experiment()
    print(f"turns {len(SCENARIO_MODES)}")
    for label in ("before", "after"):
        print(label)
        for category in CATEGORY_ORDER:
            print(f"  {category}: {results[label][category]}")
    print("repair budget after: 1 attempt per run")
    print("database writes: 0")


if __name__ == "__main__":
    main()
