"""
test per-stage timing for assistant requests (trace spans, SQL timer, the breakdown arithmetic).
"""

import time
from unittest import TestCase
from unittest.mock import patch

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.routes import assistant as assistant_route
from app.assistant import memory as memory_module
from app.assistant.loop import AssistantLoop
from app.assistant.tracing import StageTimes, sql_ms_now, start_sql_timer, summarize_stages
from app.core.database import Base
from app.models.assistant_conversation import AssistantConversation, AssistantMessage
from app.models.student_profile import StudentProfile
from app.models.user import User, UserRole
from app.schemas.assistant import AssistantChatRequest


class SlowClient:
    """a model that takes a measurable time and answers without tools."""

    def complete(self, messages, tools=None):
        time.sleep(0.05)
        return {"message": {"content": "done"}}


class ToolThenAnswerClient:
    def __init__(self):
        self.calls = 0

    def complete(self, messages, tools=None):
        self.calls += 1
        if self.calls == 1:
            return {"message": {"content": "", "tool_calls": [
                {"id": "c1", "function": {"name": "get_student_preferences", "arguments": {}}}]}}
        return {"message": {"content": "all set"}}


class StageTimesTests(TestCase):
    def test_stage_records_total_and_span(self):
        timer = StageTimes()
        with timer.stage("model_inference", iteration=1):
            time.sleep(0.02)
        self.assertGreaterEqual(timer.totals["model_inference"], 15)
        self.assertEqual(timer.spans[0]["stage"], "model_inference")
        self.assertEqual(timer.spans[0]["iteration"], 1)

    def test_stage_is_recorded_even_when_the_work_fails(self):
        timer = StageTimes()
        with self.assertRaises(RuntimeError):
            with timer.stage("tool_total"):
                raise RuntimeError("boom")
        self.assertIn("tool_total", timer.totals)

    def test_merge_shifts_span_start_times(self):
        inner = StageTimes()
        with inner.stage("model_inference"):
            pass
        outer = StageTimes()
        outer.merge(inner.totals, inner.spans, offset_ms=100.0)
        self.assertGreaterEqual(outer.spans[0]["start_ms"], 100.0)

    def test_summary_separates_tool_python_time_from_sql_time(self):
        stages = summarize_stages(model_ms=900, tool_total_ms=60, tool_sql_ms=40, sql_total_ms=70,
                                  memory_ms=10, total_ms=1100)
        self.assertEqual(stages["model_inference"], 900)
        self.assertEqual(stages["tool_execution"], 20)
        self.assertEqual(stages["database_queries"], 70)
        self.assertEqual(stages["queue_wait"], 0)
        self.assertEqual(stages["other"], 100)
        self.assertEqual(stages["total"], 1100)

    def test_other_never_goes_negative(self):
        stages = summarize_stages(model_ms=500, tool_total_ms=0, tool_sql_ms=0, sql_total_ms=0,
                                  memory_ms=0, total_ms=400)
        self.assertEqual(stages["other"], 0)


class SqlTimerTests(TestCase):
    def test_sql_time_is_counted_per_request(self):
        engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
        start_sql_timer()
        with Session(engine) as session:
            session.execute(text("select 1"))
            session.execute(text("select 2"))
        self.assertGreater(sql_ms_now(), 0)
        before = sql_ms_now()
        start_sql_timer()
        self.assertEqual(sql_ms_now(), 0.0)
        self.assertGreater(before, 0)


class LoopTimingTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(cls.engine)

    def setUp(self):
        memory_module._fallback_database = None
        self.db = Session(self.engine)
        self.user = User(role=UserRole.STUDENT, email="trace@example.com", password_hash="x")
        self.student = StudentProfile(user=self.user, full_name="Trace Student", college_name="Test College")
        self.db.add_all([self.user, self.student])
        self.db.commit()
        self.db.refresh(self.user)

    def tearDown(self):
        self.db.query(AssistantMessage).delete()
        self.db.query(AssistantConversation).delete()
        self.db.query(StudentProfile).delete()
        self.db.query(User).delete()
        self.db.commit()
        self.db.close()

    def test_run_reports_model_time_and_spans(self):
        result = AssistantLoop(client=SlowClient()).run(self.db, self.user.id, "hello")
        self.assertGreaterEqual(result.stage_ms["model_inference"], 40)
        self.assertEqual([s["stage"] for s in result.trace_spans], ["model_inference"])

    def test_tool_call_adds_tool_spans_and_sql_time(self):
        start_sql_timer()
        result = AssistantLoop(client=ToolThenAnswerClient()).run(self.db, self.user.id, "what are my preferences")
        stages = [s["stage"] for s in result.trace_spans]
        self.assertEqual(stages, ["model_inference", "tool_total", "model_inference"])
        self.assertEqual(result.trace_spans[1]["tool"], "get_student_preferences")
        self.assertGreater(result.stage_ms["tool_sql"], 0)
        self.assertGreaterEqual(result.stage_ms["tool_total"], result.stage_ms["tool_sql"])

    def test_chat_response_carries_stage_timing_for_ok_and_failed_traces(self):
        with patch.object(assistant_route, "AssistantLoop", lambda: AssistantLoop(client=SlowClient())):
            ok = assistant_route.chat_with_assistant(
                request=AssistantChatRequest(message="hi"), current_user=self.user, db=self.db, x_trace_id="ok-trace")
        self.assertEqual(ok.trace_id, "ok-trace")
        self.assertIsNone(ok.failure_mode)
        for stage in ("model_inference", "database_queries", "tool_execution", "memory_store", "queue_wait", "other", "total"):
            self.assertIn(stage, ok.stage_timing_ms)
        self.assertGreaterEqual(ok.stage_timing_ms["model_inference"], 40)
        self.assertGreater(ok.stage_timing_ms["database_queries"], 0)
        self.assertGreaterEqual(ok.stage_timing_ms["total"], ok.stage_timing_ms["model_inference"])
        self.assertEqual(ok.trace_spans[0]["stage"] in {"memory_store", "model_inference"}, True)

        from app.services.ollama_client import OllamaError

        class DownClient:
            def complete(self, messages, tools=None):
                raise OllamaError("connection refused")

        with patch.object(assistant_route, "AssistantLoop", lambda: AssistantLoop(client=DownClient())):
            failed = assistant_route.chat_with_assistant(
                request=AssistantChatRequest(message="hi"), current_user=self.user, db=self.db, x_trace_id="failed-trace")
        self.assertEqual(failed.failure_mode, "ollama_error")
        self.assertEqual(failed.trace_id, "failed-trace")
        self.assertIn("total", failed.stage_timing_ms)
        self.assertEqual(failed.trace_spans[-1]["stage"], "model_inference")
