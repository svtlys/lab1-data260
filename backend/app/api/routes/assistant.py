"""
authenticated API route for the hand-built assistant.
"""

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_student
from app.assistant.context import clean_trace_id
from app.assistant.memory import get_memory_database, handle_memory_command, is_memory_command
from app.assistant.loop import AssistantLoop, AssistantRunResult
from app.core.database import get_db
from app.models.assistant_conversation import AssistantConversation, AssistantMessage
from app.models.assistant_tool_log import AssistantToolLog
from app.models.student_profile import StudentProfile
from app.models.user import User
from app.schemas.assistant import (
    AssistantChatRequest,
    AssistantChatResponse,
    AssistantToolCallResponse,
)


# group assistant endpoints under /api/assistant
router = APIRouter(
    prefix="/api/assistant",
    tags=["assistant"],
)


def find_student_profile(current_user: User, db: Session) -> StudentProfile:
    """find the profile belonging to the logged-in student."""

    profile = db.scalar(
        select(StudentProfile).where(
            StudentProfile.user_id == current_user.id,
        )
    )

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="student profile was not found",
        )

    return profile


def load_history(
    conversation_id: int,
    db: Session,
) -> list[dict[str, str]]:
    """load prior messages in the format expected by the assistant loop."""

    statement = (
        select(AssistantMessage)
        .where(AssistantMessage.conversation_id == conversation_id)
        .order_by(AssistantMessage.sequence_number.asc())
    )
    return [
        {"role": message.role, "content": message.content}
        for message in db.scalars(statement).all()
        if message.role != "system"
    ]


def next_sequence_number(conversation_id: int, db: Session) -> int:
    """return the next ordered message number for a conversation."""

    last_message = db.scalar(
        select(AssistantMessage)
        .where(AssistantMessage.conversation_id == conversation_id)
        .order_by(AssistantMessage.sequence_number.desc())
    )
    return (last_message.sequence_number + 1) if last_message else 1


def normalize_json_value(value: Any) -> Any:
    """convert tool metadata into JSON-compatible values."""

    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    try:
        json.dumps(value)
        return value
    except TypeError:
        return str(value)


@router.post("/chat", response_model=AssistantChatResponse)
def chat_with_assistant(
    request: AssistantChatRequest,
    current_user: User = Depends(require_student),
    db: Session = Depends(get_db),
    x_trace_id: str | None = Header(default=None),
):
    """run one bounded assistant turn and persist its conversation trace."""

    student_profile = find_student_profile(current_user, db)
    conversation = None

    if request.conversation_id is not None:
        conversation = db.scalar(
            select(AssistantConversation).where(
                AssistantConversation.id == request.conversation_id,
                AssistantConversation.student_id == student_profile.id,
            )
        )

        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="assistant conversation was not found",
            )

    if conversation is None:
        conversation = AssistantConversation(student_id=student_profile.id)
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    history = load_history(conversation.id, db)
    trace_id = clean_trace_id(x_trace_id)
    if is_memory_command(request.message):
        memory_database = get_memory_database()
        answer = handle_memory_command(
            memory_database,
            current_user.id,
            request.message,
            trace_id=trace_id,
        )
        result = AssistantRunResult(
            answer=answer,
            messages=[
                {"role": "system", "content": "/memory command"},
                *history,
                {"role": "user", "content": request.message},
                {"role": "assistant", "content": answer},
            ],
            trace_id=trace_id,
        )
    else:
        loop = AssistantLoop()
        result = loop.run(
            db=db,
            student_id=current_user.id,
            user_message=request.message,
            history=history,
            confirmed_save=request.confirm_save,
            trace_id=trace_id,
        )

    # save only the new messages from this assistant turn
    new_messages = result.messages[1 + len(history):]
    sequence_number = next_sequence_number(conversation.id, db)
    for message in new_messages:
        db.add(
            AssistantMessage(
                conversation_id=conversation.id,
                role=message.get("role", "assistant"),
                content=message.get("content", ""),
                sequence_number=sequence_number,
            )
        )
        sequence_number += 1

    # save each tool call as grading and debugging evidence
    for tool_call in result.tool_calls:
        db.add(
            AssistantToolLog(
                conversation_id=conversation.id,
                iteration=tool_call["iteration"],
                tool_call_id=tool_call["tool_call_id"],
                tool_name=tool_call["tool_name"],
                arguments_json=normalize_json_value(tool_call.get("arguments", {})),
                result_json=normalize_json_value(tool_call["result"])
                if "result" in tool_call
                else None,
                error_message=tool_call.get("error"),
            )
        )

    conversation.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()

    return AssistantChatResponse(
        conversation_id=conversation.id,
        answer=result.answer,
        iterations=result.iterations,
        tool_call_count=result.tool_call_count,
        repair_attempts=result.repair_attempts,
        failure_mode=result.failure_mode,
        reached_iteration_ceiling=result.reached_iteration_ceiling,
        tool_calls=[
            AssistantToolCallResponse(
                iteration=tool_call["iteration"],
                tool_call_id=tool_call["tool_call_id"],
                tool_name=tool_call["tool_name"],
                arguments=normalize_json_value(tool_call.get("arguments", {})),
                result=normalize_json_value(tool_call["result"])
                if "result" in tool_call
                else None,
                error=tool_call.get("error"),
            )
            for tool_call in result.tool_calls
        ],
        created_at=conversation.created_at,
        trace_id=result.trace_id or trace_id,
        token_usage=result.token_usage,
        compaction=result.compaction,
    )
