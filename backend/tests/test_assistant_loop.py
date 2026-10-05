"""
test the bounded manual assistant loop without calling Ollama.
"""

from datetime import datetime
from unittest import TestCase

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.assistant.loop import AssistantLoop
from app.core.database import Base
from app.models.job import Job
from app.models.student_profile import StudentProfile
from app.models.user import User, UserRole


class FakeOllamaClient:
    """return predetermined responses for loop tests."""

    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def chat(self, messages, tools=None):
        # record the conversation sent to the fake model
        self.calls.append({"messages": messages, "tools": tools})
        return next(self.responses)


class AssistantLoopTests(TestCase):
    """verify tool execution and the iteration ceiling."""

    @classmethod
    def setUpClass(cls):
        # create one isolated database for loop tests
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(cls.engine)

    def setUp(self):
        # create a student and one searchable job
        self.db = Session(self.engine)
        self.user = User(
            role=UserRole.STUDENT,
            email="loop-test@example.com",
            password_hash="test-hash",
        )
        self.student = StudentProfile(
            user=self.user,
            full_name="Loop Test Student",
            college_name="Test College",
        )
        self.job = Job(
            title="Loop Python Internship",
            description="Build a test service.",
            company_name="Loop Labs",
            location="Sunnyvale office",
            city="Sunnyvale",
            employment_type="internship",
            is_remote=False,
            required_skills="Python",
            posted_at=datetime(2026, 10, 1, 9, 0),
        )
        self.db.add_all([self.user, self.student, self.job])
        self.db.commit()
        self.db.refresh(self.user)

    def tearDown(self):
        # remove isolated test data before closing the session
        self.db.query(Job).delete()
        self.db.query(StudentProfile).delete()
        self.db.query(User).delete()
        self.db.commit()
        self.db.close()

    def test_loop_executes_tool_and_returns_final_answer(self):
        """execute a requested tool and send its result back to the model."""

        fake_client = FakeOllamaClient(
            [
                {
                    "message": {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "call-1",
                                "function": {
                                    "name": "search_jobs",
                                    "arguments": {"city": "Sunnyvale"},
                                },
                            }
                        ],
                    }
                },
                {
                    "message": {
                        "role": "assistant",
                        "content": "I found one Sunnyvale internship.",
                    }
                },
            ]
        )
        loop = AssistantLoop(client=fake_client, max_iterations=3)

        result = loop.run(self.db, self.user.id, "find me a Sunnyvale job")

        self.assertEqual(result.answer, "I found one Sunnyvale internship.")
        self.assertEqual(result.iterations, 2)
        self.assertFalse(result.reached_iteration_ceiling)
        self.assertEqual(result.tool_calls[0]["tool_name"], "search_jobs")
        self.assertEqual(len(fake_client.calls), 2)

    def test_loop_stops_at_iteration_ceiling(self):
        """stop when the model keeps requesting tools indefinitely."""

        repeated_tool_response = {
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call-loop",
                        "function": {
                            "name": "search_jobs",
                            "arguments": {},
                        },
                    }
                ],
            }
        }
        fake_client = FakeOllamaClient([repeated_tool_response])
        loop = AssistantLoop(client=fake_client, max_iterations=1)

        result = loop.run(self.db, self.user.id, "keep searching")

        self.assertTrue(result.reached_iteration_ceiling)
        self.assertEqual(result.iterations, 1)
        self.assertIn("tool-call limit", result.answer)


if __name__ == "__main__":
    # run the loop tests directly without requiring a separate test runner
    import unittest

    unittest.main()
