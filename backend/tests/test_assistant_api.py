"""
test assistant API persistence without calling the Ollama service.
"""

from datetime import datetime
from unittest import TestCase
from unittest.mock import patch

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.routes import assistant as assistant_route
from app.assistant.loop import AssistantRunResult
from app.core.database import Base
from app.models.assistant_conversation import AssistantConversation, AssistantMessage
from app.models.assistant_tool_log import AssistantToolLog
from app.models.student_profile import StudentProfile
from app.models.user import User, UserRole
from app.schemas.assistant import AssistantChatRequest


class FakeAssistantLoop:
    """return a predictable assistant result for the endpoint test."""

    def __init__(self):
        self.max_iterations = 5

    def run(self, db, student_id, user_message, history):
        # return one assistant turn with one logged tool call
        return AssistantRunResult(
            answer="I found a useful opportunity.",
            messages=[
                {"role": "system", "content": "system"},
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": "I found a useful opportunity."},
            ],
            tool_calls=[
                {
                    "iteration": 1,
                    "tool_call_id": "test-call-1",
                    "tool_name": "search_jobs",
                    "arguments": {"city": "Sunnyvale"},
                    "result": {"count": 1},
                }
            ],
            iterations=1,
        )


class AssistantApiTests(TestCase):
    """verify conversation and tool-log persistence."""

    @classmethod
    def setUpClass(cls):
        # create an isolated database for the endpoint test
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(cls.engine)

    def setUp(self):
        # create one authenticated student profile
        self.db = Session(self.engine)
        self.user = User(
            role=UserRole.STUDENT,
            email="assistant-api-test@example.com",
            password_hash="test-hash",
        )
        self.student = StudentProfile(
            user=self.user,
            full_name="Assistant API Student",
            college_name="Test College",
        )
        self.db.add_all([self.user, self.student])
        self.db.commit()
        self.db.refresh(self.user)

    def tearDown(self):
        # clear endpoint records before closing the isolated session
        self.db.query(AssistantToolLog).delete()
        self.db.query(AssistantMessage).delete()
        self.db.query(AssistantConversation).delete()
        self.db.query(StudentProfile).delete()
        self.db.query(User).delete()
        self.db.commit()
        self.db.close()

    def test_chat_persists_conversation_messages_and_tool_log(self):
        """persist the assistant answer and its tool-call evidence."""

        request = AssistantChatRequest(message="find me a job")
        with patch.object(assistant_route, "AssistantLoop", FakeAssistantLoop):
            response = assistant_route.chat_with_assistant(
                request=request,
                current_user=self.user,
                db=self.db,
            )

        conversation = self.db.get(
            AssistantConversation,
            response.conversation_id,
        )
        messages = list(
            self.db.scalars(
                select(AssistantMessage).where(
                    AssistantMessage.conversation_id == conversation.id,
                )
            ).all()
        )
        tool_logs = list(
            self.db.scalars(
                select(AssistantToolLog).where(
                    AssistantToolLog.conversation_id == conversation.id,
                )
            ).all()
        )

        self.assertEqual(response.answer, "I found a useful opportunity.")
        self.assertIsNotNone(response.created_at)
        self.assertEqual(len(messages), 2)
        self.assertEqual(len(tool_logs), 1)
        self.assertEqual(tool_logs[0].tool_name, "search_jobs")


if __name__ == "__main__":
    # run the API test directly without requiring a separate test runner
    import unittest

    unittest.main()
