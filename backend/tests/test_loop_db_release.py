"""
the assistant loop must give its database connection back before each (slow) model call.

found with JMeter in Lab 2: every in-flight chat kept a pooled MySQL connection for the whole model
call, so 20+ concurrent chats used up the pool and other requests (logins) failed with HTTP 500.
"""

from unittest import TestCase

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.assistant.loop import AssistantLoop
from app.core.database import Base


class CountingSession(Session):
    """a Session that counts how often the transaction was ended with rollback."""

    rollbacks = 0

    def rollback(self):
        self.rollbacks += 1
        super().rollback()


class SpyClient:
    """record how many rollbacks had happened at the moment of each model call."""

    def __init__(self, db):
        self.db = db
        self.rollbacks_at_call = []
        self.replies = iter([
            {"message": {"role": "assistant", "content": "", "tool_calls": [
                {"id": "1", "function": {"name": "search_jobs", "arguments": {"query": "Python"}}}]}},
            {"message": {"role": "assistant", "content": "done"}},
        ])

    def chat(self, messages, tools=None):
        self.rollbacks_at_call.append(self.db.rollbacks)
        return next(self.replies)


class LoopDatabaseReleaseTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(cls.engine)

    def test_connection_is_released_before_every_model_call(self):
        db = CountingSession(self.engine)
        client = SpyClient(db)

        result = AssistantLoop(client=client).run(db, 1, "find Python jobs")
        db.close()

        self.assertEqual(result.answer, "done")
        # before model call 1 there was 1 rollback, before call 2 there were 2
        self.assertEqual(client.rollbacks_at_call, [1, 2])
