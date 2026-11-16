"""
per-stage timing for one assistant request (Lab 2, Part 6, tracing).

every request already carries a trace_id (see app.assistant.context). this module adds the time spent
in each stage, so a trace can answer "where did the time go?":

* model_inference    time waiting for Ollama (all model calls of the request)
* database_queries   time the database spent running SQL (measured on the SQLAlchemy cursor, so it
                     covers the history load, the tools' queries and the saves)
* tool_execution     time inside the tool functions that was not SQL (validation, filtering, formatting)
* memory_store       time reading and writing student memory and the conversation copy (Mongo)
* queue_wait         time an event sat in Kafka before a worker took it. an assistant chat is
                     synchronous, so it is 0 here; workers log it per event (queue_wait_ms)
* other              everything else (request validation, summaries, serialising the response)

the SQL timer is a context variable, so each request thread keeps its own total.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import Engine

STAGES = ("model_inference", "database_queries", "tool_execution", "memory_store", "queue_wait", "other")

_sql_total_ms: ContextVar[list[float] | None] = ContextVar("sql_total_ms", default=None)


def start_sql_timer() -> None:
    """start counting SQL time for the current request."""
    _sql_total_ms.set([0.0])


def sql_ms_now() -> float:
    """SQL time counted so far in the current request, in milliseconds."""
    counter = _sql_total_ms.get()
    return counter[0] if counter else 0.0


@event.listens_for(Engine, "before_cursor_execute")
def _sql_started(connection, cursor, statement, parameters, context, executemany):
    connection.info.setdefault("_trace_sql_starts", []).append(time.perf_counter())


@event.listens_for(Engine, "after_cursor_execute")
def _sql_finished(connection, cursor, statement, parameters, context, executemany):
    starts = connection.info.get("_trace_sql_starts")
    if not starts:
        return
    elapsed_ms = (time.perf_counter() - starts.pop()) * 1000
    counter = _sql_total_ms.get()
    if counter is not None:
        counter[0] += elapsed_ms


class StageTimes:
    """collect named durations and ordered spans for one piece of work."""

    def __init__(self) -> None:
        self._t0 = time.perf_counter()
        self.totals: dict[str, float] = {}
        self.spans: list[dict[str, Any]] = []

    def now_ms(self) -> float:
        return (time.perf_counter() - self._t0) * 1000

    @contextmanager
    def stage(self, name: str, **labels: Any):
        started = time.perf_counter()
        try:
            yield
        finally:
            ms = (time.perf_counter() - started) * 1000
            self.totals[name] = self.totals.get(name, 0.0) + ms
            self.spans.append({"stage": name, "start_ms": round((started - self._t0) * 1000, 1),
                               "ms": round(ms, 1), **labels})

    def add(self, name: str, ms: float) -> None:
        """add time to a total without recording a span."""
        self.totals[name] = self.totals.get(name, 0.0) + ms

    def merge(self, totals: dict[str, float] | None, spans: list[dict[str, Any]] | None, offset_ms: float) -> None:
        """bring in another timer's numbers; its spans started `offset_ms` after this timer."""
        for name, ms in (totals or {}).items():
            self.add(name, ms)
        for span in spans or []:
            self.spans.append({**span, "start_ms": round(span["start_ms"] + offset_ms, 1)})


def summarize_stages(
    *,
    model_ms: float,
    tool_total_ms: float,
    tool_sql_ms: float,
    sql_total_ms: float,
    memory_ms: float,
    total_ms: float,
    queue_wait_ms: float = 0.0,
) -> dict[str, float]:
    """turn raw timings into the stage breakdown (every stage, in ms, plus the total)."""
    tool_python_ms = max(tool_total_ms - tool_sql_ms, 0.0)
    named = model_ms + sql_total_ms + tool_python_ms + memory_ms + queue_wait_ms
    breakdown = {
        "model_inference": model_ms,
        "database_queries": sql_total_ms,
        "tool_execution": tool_python_ms,
        "memory_store": memory_ms,
        "queue_wait": queue_wait_ms,
        "other": max(total_ms - named, 0.0),
    }
    result = {name: round(value, 1) for name, value in breakdown.items()}
    result["total"] = round(total_ms, 1)
    return result
