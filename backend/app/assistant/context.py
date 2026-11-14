"""
token tracking, the 70% warning and conversation compaction for the assistant (Lab 2, Part 6).

the model has a fixed context window (settings.assistant_context_tokens, passed to Ollama as
num_ctx). three things are done here:

* track: after every model call, record how many tokens were used (Ollama reports
  prompt_eval_count / eval_count; when a client does not, we estimate 1 token per 4 characters).
* warn: once the conversation uses more than 70% of the window, the run is flagged so the student
  is told the conversation is getting long.
* compact: once it passes 85%, the copy of the conversation sent to the model is shrunk (old tool
  output is truncated, older turns are replaced by a short summary) so the next call still fits.
  the stored conversation is never changed, only what the model is shown.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from typing import Any

CHARS_PER_TOKEN = 4
PER_MESSAGE_OVERHEAD = 4  # role markers and separators
WARNING_FRACTION = 0.70  # warn when more than this share of the window is used
COMPACT_FRACTION = 0.85  # compact when more than this share is used
KEEP_RECENT_MESSAGES = 4  # most recent history messages kept word for word
TOOL_RESULT_KEEP_CHARS = 300  # old tool results are cut to this many characters
SUMMARY_LINE_CHARS = 120
SUMMARY_MAX_LINES = 12

_TRACE_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


# ---------------------------------------------------------------------------
# trace ids
# ---------------------------------------------------------------------------
def new_trace_id() -> str:
    """create a fresh trace id (a UUID string, so it fits the Kafka event envelope)."""
    return str(uuid.uuid4())


def trace_uuid(trace_id: str) -> uuid.UUID:
    """return the trace id as a UUID; other safe ids map to a fixed UUID so events can still carry them."""
    try:
        return uuid.UUID(trace_id)
    except ValueError:
        return uuid.uuid5(uuid.NAMESPACE_URL, f"p16-trace:{trace_id}")


def clean_trace_id(value: Any) -> str:
    """accept a caller's trace id if it is safe to log, otherwise make a new one."""
    if isinstance(value, str) and _TRACE_ID_PATTERN.match(value):
        return value
    return new_trace_id()


# ---------------------------------------------------------------------------
# counting tokens
# ---------------------------------------------------------------------------
def estimate_tokens(messages: list[dict[str, Any]]) -> int:
    """cheap token estimate for a list of chat messages (about 4 characters per token)."""
    total = 0
    for message in messages:
        text = str(message.get("content") or "")
        if message.get("tool_calls"):
            text += json.dumps(message["tool_calls"], default=str)
        total += len(text) // CHARS_PER_TOKEN + PER_MESSAGE_OVERHEAD
    return total


@dataclass
class TokenTracker:
    """add up token use over one assistant run and decide when to warn."""

    budget: int
    model_calls: int = 0
    prompt_tokens_total: int = 0
    completion_tokens_total: int = 0
    last_prompt_tokens: int = 0
    last_completion_tokens: int = 0
    estimated: bool = False
    peak_fraction: float = 0.0
    history: list[dict[str, Any]] = field(default_factory=list)

    def record(self, response: dict[str, Any], sent_messages: list[dict[str, Any]]) -> None:
        """record one model call; use the counts Ollama reports, else estimate."""
        prompt = response.get("prompt_eval_count")
        completion = response.get("eval_count")
        if not isinstance(prompt, int):
            prompt = estimate_tokens(sent_messages)
            self.estimated = True
        if not isinstance(completion, int):
            reply = response.get("message") if isinstance(response.get("message"), dict) else {}
            completion = estimate_tokens([reply]) if reply else 0
            self.estimated = True

        self.model_calls += 1
        self.prompt_tokens_total += prompt
        self.completion_tokens_total += completion
        self.last_prompt_tokens = prompt
        self.last_completion_tokens = completion
        fraction = (prompt + completion) / self.budget if self.budget else 0.0
        self.peak_fraction = max(self.peak_fraction, fraction)
        self.history.append(
            {"call": self.model_calls, "prompt_tokens": prompt, "completion_tokens": completion,
             "context_fraction": round(fraction, 3)}
        )

    @property
    def context_fraction(self) -> float:
        """share of the window used by the latest call (prompt plus reply)."""
        if not self.budget:
            return 0.0
        return (self.last_prompt_tokens + self.last_completion_tokens) / self.budget

    @property
    def warning(self) -> bool:
        """true once more than 70% of the window was used at any point in this run."""
        return self.peak_fraction > WARNING_FRACTION

    def snapshot(self) -> dict[str, Any]:
        """JSON-ready summary for the API response, logs and harness report."""
        return {
            "model_calls": self.model_calls,
            "prompt_tokens": self.prompt_tokens_total,
            "completion_tokens": self.completion_tokens_total,
            "total_tokens": self.prompt_tokens_total + self.completion_tokens_total,
            "context_budget": self.budget,
            "context_used": self.last_prompt_tokens + self.last_completion_tokens,
            "context_fraction": round(self.context_fraction, 3),
            "peak_fraction": round(self.peak_fraction, 3),
            "warning_threshold": WARNING_FRACTION,
            "warning": self.warning,
            "estimated": self.estimated,
        }


# ---------------------------------------------------------------------------
# compaction
# ---------------------------------------------------------------------------
def _clip(text: str, limit: int) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _summarise(dropped: list[dict[str, Any]]) -> str:
    """short extractive summary of dropped history (no model call, so it is cheap and repeatable)."""
    lines = [
        f"- {m.get('role', 'user')}: {_clip(m.get('content', ''), SUMMARY_LINE_CHARS)}"
        for m in dropped
        if m.get("content")
    ]
    if len(lines) > SUMMARY_MAX_LINES:
        omitted = len(lines) - SUMMARY_MAX_LINES
        lines = [f"- ({omitted} earlier messages not listed)"] + lines[-SUMMARY_MAX_LINES:]
    return "summary of the earlier conversation (older messages were compacted):\n" + "\n".join(lines)


def compact_messages(
    messages: list[dict[str, Any]],
    budget: int,
    fraction: float = COMPACT_FRACTION,
    keep_recent: int = KEEP_RECENT_MESSAGES,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """return (messages_for_the_model, info); the input list is never modified.

    nothing happens until the estimate passes `fraction` of the window. then:
      1. tool results from earlier iterations are cut short;
      2. if that is not enough, history before the newest user message is replaced by a summary
         (the system prompt, the last `keep_recent` history messages and everything from the
         current user message onward are always kept, so tool calls stay paired with results).
    """
    before = estimate_tokens(messages)
    info: dict[str, Any] = {"compacted": False, "tokens_before": before, "tokens_after": before,
                            "tool_results_truncated": 0, "messages_summarised": 0}
    if not budget or before <= budget * fraction:
        return messages, info

    working = [dict(m) for m in messages]

    # position of the current user message: the last one with role "user"
    current = max((i for i, m in enumerate(working) if m.get("role") == "user"), default=len(working) - 1)

    # step 1: shorten tool output that is not from the newest tool round
    last_tool = max((i for i, m in enumerate(working) if m.get("role") == "tool"), default=-1)
    for i, message in enumerate(working):
        if message.get("role") == "tool" and i != last_tool:
            content = str(message.get("content") or "")
            if len(content) > TOOL_RESULT_KEEP_CHARS:
                message["content"] = content[:TOOL_RESULT_KEEP_CHARS] + " …[older tool result truncated]"
                info["tool_results_truncated"] += 1

    # step 2: summarise old history if still too big
    if estimate_tokens(working) > budget * fraction:
        start = 1 if working and working[0].get("role") == "system" else 0
        history = working[start:current]
        if len(history) > keep_recent:
            dropped, kept = history[:-keep_recent] if keep_recent else history, history[-keep_recent:] if keep_recent else []
            summary = {"role": "system", "content": _summarise(dropped)}
            working = working[:start] + [summary] + kept + working[current:]
            info["messages_summarised"] = len(dropped)

    info["compacted"] = bool(info["tool_results_truncated"] or info["messages_summarised"])
    info["tokens_after"] = estimate_tokens(working)
    return (working, info) if info["compacted"] else (messages, info)
