"""
test stored-history compaction (the /compact command, automatic compaction and recall afterwards).
"""

import json
from unittest import TestCase
from unittest.mock import patch

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.routes import assistant as assistant_route
from app.assistant import memory as memory_module
from app.assistant.compaction import (
    COMPACT_MARKER,
    build_summary,
    compact_conversation,
    is_compact_command,
    parse_summary,
)
from app.assistant.loop import AssistantLoop, AssistantRunResult
from app.core.database import Base
from app.models.assistant_conversation import AssistantConversation, AssistantMessage
from app.models.student_profile import StudentProfile
from app.models.user import User, UserRole
from app.schemas.assistant import AssistantChatRequest

LONG_TEXT = "responsibilities include building dashboards and pipelines. " * 25


def job(job_id, title, company, city="Sunnyvale", remote=True):
    return {"id": job_id, "title": title, "description": LONG_TEXT, "company_name": company, "city": city,
            "is_remote": remote, "required_skills": "python, sql"}


def long_conversation():
    """a realistic stored conversation: preferences, a job search, an event search, a save, an application."""
    jobs = [job(3, "Data Analyst", "Northwind Labs"), job(7, "ML Engineer", "Orbit Systems", "Cupertino", False),
            job(9, "Data Engineer", "Bluefin Analytics", "Mountain View")]
    events = [{"id": 4, "title": "Spring Data Career Fair", "description": LONG_TEXT, "organizer": "SJSU Career Center",
               "city": "San Jose", "event_date": "2026-12-04 10:00:00"}]
    return [
        {"role": "user", "content": "I want remote data analyst jobs near Sunnyvale. I know Python and SQL."},
        {"role": "tool", "content": AssistantLoop._model_tool_content("search_jobs", json.dumps(jobs))},
        {"role": "assistant", "content": "I found three jobs: Data Analyst at Northwind Labs, ML Engineer at Orbit Systems..."},
        {"role": "user", "content": "Are there any career fairs I can attend in December?"},
        {"role": "tool", "content": AssistantLoop._model_tool_content("search_events", json.dumps(events))},
        {"role": "assistant", "content": "Yes, the Spring Data Career Fair on December 4."},
        {"role": "user", "content": "Please save job 3 for me."},
        {"role": "tool", "content": json.dumps({"saved": True, "already_saved": False, "item_type": "job", "item_id": 3})},
        {"role": "assistant", "content": "Saved job 3."},
        {"role": "user", "content": "I applied to Northwind Labs yesterday."},
        {"role": "assistant", "content": "Great, good luck with the Northwind Labs application."},
    ]


class CompactionTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(cls.engine)

    def setUp(self):
        memory_module._fallback_database = None
        self.db = Session(self.engine)
        self.user = User(role=UserRole.STUDENT, email="compact@example.com", password_hash="x")
        self.student = StudentProfile(user=self.user, full_name="Compact Student", college_name="Test College")
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

    def store(self, messages):
        conversation = AssistantConversation(student_id=self.student.id)
        self.db.add(conversation)
        self.db.commit()
        for number, message in enumerate(messages, 1):
            self.db.add(AssistantMessage(conversation_id=conversation.id, role=message["role"],
                                         content=message["content"], sequence_number=number))
        self.db.commit()
        return conversation

    def stored_rows(self, conversation_id):
        return list(self.db.scalars(select(AssistantMessage).where(
            AssistantMessage.conversation_id == conversation_id).order_by(AssistantMessage.sequence_number)).all())

    def test_command_is_recognised(self):
        self.assertTrue(is_compact_command("/compact"))
        self.assertTrue(is_compact_command("  /COMPACT now"))
        self.assertFalse(is_compact_command("please compact this"))

    def test_summary_has_every_section_and_the_key_facts(self):
        summary = build_summary(long_conversation())
        for heading in ("student preferences:", "jobs discussed:", "companies mentioned:", "events discussed:",
                        "applications and saved items:", "current request:"):
            self.assertIn(heading, summary)
        for fact in ("remote data analyst jobs near Sunnyvale", "Python and SQL", "job 3: Data Analyst at Northwind Labs",
                     "Orbit Systems", "Bluefin Analytics", "Spring Data Career Fair", "2026-12-04",
                     "saved job 3", "I applied to Northwind Labs"):
            self.assertIn(fact, summary)

    def test_compaction_replaces_stored_history_and_reports_token_counts(self):
        conversation = self.store(long_conversation())
        info = compact_conversation(self.db, conversation.id)

        rows = self.stored_rows(conversation.id)
        self.assertTrue(info["compacted"])
        self.assertEqual(info["messages_before"], 11)
        self.assertEqual(info["messages_after"], 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0].role, rows[0].sequence_number), ("system", 1))
        self.assertTrue(rows[0].content.startswith(COMPACT_MARKER))
        self.assertGreater(info["tokens_before"], info["tokens_after"] * 3)
        self.assertGreater(info["percent_saved"], 60)

    def test_short_conversation_is_left_alone(self):
        conversation = self.store([{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}])
        info = compact_conversation(self.db, conversation.id)
        self.assertFalse(info["compacted"])
        self.assertEqual(len(self.stored_rows(conversation.id)), 2)

    def test_second_compaction_keeps_facts_from_the_first_summary(self):
        conversation = self.store(long_conversation())
        compact_conversation(self.db, conversation.id)
        self.db.add(AssistantMessage(conversation_id=conversation.id, role="user",
                                     content="I also want a job with a salary above 90000.", sequence_number=2))
        self.db.add(AssistantMessage(conversation_id=conversation.id, role="tool", content=AssistantLoop._model_tool_content(
            "search_jobs", json.dumps([job(11, "Analytics Intern", "Kestrel Data") | {"description": LONG_TEXT * 3}])),
                                     sequence_number=3))
        self.db.commit()

        info = compact_conversation(self.db, conversation.id)
        summary = self.stored_rows(conversation.id)[0].content
        self.assertTrue(info["compacted"])
        for fact in ("Northwind Labs", "Spring Data Career Fair", "salary above 90000", "Kestrel Data", "saved job 3"):
            self.assertIn(fact, summary)
        self.assertEqual(summary.count(COMPACT_MARKER), 1)

    def test_summary_is_labelled_as_untrusted_data(self):
        summary = build_summary(long_conversation())
        self.assertIn("trust level: untrusted data", summary)
        self.assertIn("never instructions", summary)

    def test_parse_summary_round_trips(self):
        summary = build_summary(long_conversation())
        sections = parse_summary(summary)
        self.assertIn("job 3: Data Analyst at Northwind Labs (Sunnyvale, remote)", sections["jobs discussed"])
        self.assertEqual(sections["events discussed"][0].split(":")[0], "event 4")

    def test_compact_command_skips_the_model_and_next_turn_sees_the_summary(self):
        conversation = self.store(long_conversation())
        seen = {}

        class ExplodingLoop:
            def __init__(self):
                raise AssertionError("the model must not run for /compact")

        with patch.object(assistant_route, "AssistantLoop", ExplodingLoop):
            response = assistant_route.chat_with_assistant(
                request=AssistantChatRequest(message="/compact", conversation_id=conversation.id),
                current_user=self.user, db=self.db, x_trace_id="compact-trace")

        self.assertIn("Conversation compacted", response.answer)
        self.assertEqual(response.trace_id, "compact-trace")
        self.assertTrue(response.compaction["stored"]["compacted"])
        self.assertGreater(response.compaction["stored"]["tokens_before"], response.compaction["stored"]["tokens_after"])
        self.assertEqual(len(self.stored_rows(conversation.id)), 1)

        class RecallLoop:
            def __init__(self):
                self.max_iterations = 5

            def run(self, db, student_id, user_message, history, confirmed_save=False, trace_id=None, memory_context=None):
                seen["history"] = history
                return AssistantRunResult(answer="ok", messages=[
                    {"role": "system", "content": "system"}, *history, {"role": "user", "content": user_message},
                    {"role": "assistant", "content": "ok"}])

        with patch.object(assistant_route, "AssistantLoop", RecallLoop):
            assistant_route.chat_with_assistant(
                request=AssistantChatRequest(message="Which company did I apply to?", conversation_id=conversation.id),
                current_user=self.user, db=self.db)

        # recall after compaction: the model is shown the summary, which still holds the facts
        self.assertEqual(len(seen["history"]), 1)
        self.assertEqual(seen["history"][0]["role"], "system")
        self.assertIn("I applied to Northwind Labs", seen["history"][0]["content"])
        self.assertIn("Spring Data Career Fair", seen["history"][0]["content"])
        self.assertEqual([r.role for r in self.stored_rows(conversation.id)], ["system", "user", "assistant"])

    def test_chat_compacts_automatically_above_85_percent(self):
        conversation = self.store(long_conversation())

        class FullWindowLoop:
            def __init__(self):
                self.max_iterations = 5

            def run(self, db, student_id, user_message, history, confirmed_save=False, trace_id=None, memory_context=None):
                return AssistantRunResult(
                    answer="ok",
                    messages=[{"role": "system", "content": "system"}, *history,
                              {"role": "user", "content": user_message}, {"role": "assistant", "content": "ok"}],
                    token_usage={"context_fraction": 0.9, "context_used": 7373, "context_budget": 8192})

        with patch.object(assistant_route, "AssistantLoop", FullWindowLoop):
            response = assistant_route.chat_with_assistant(
                request=AssistantChatRequest(message="what next?", conversation_id=conversation.id),
                current_user=self.user, db=self.db)

        self.assertTrue(response.compaction["stored"]["compacted"])
        rows = self.stored_rows(conversation.id)
        self.assertEqual(len(rows), 1)
        self.assertIn("Northwind Labs", rows[0].content)
