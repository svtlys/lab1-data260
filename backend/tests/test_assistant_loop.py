"""
test the bounded manual assistant loop without calling Ollama.
"""

from datetime import datetime
import json
from unittest import TestCase
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.assistant.loop import AssistantLoop
from app.core.database import Base
from app.models.job import Job
from app.models.saved_item import SavedItem
from app.models.student_profile import StudentProfile
from app.models.user import User, UserRole
from app.services.ollama_client import OllamaClient, OllamaError


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
        self.db.query(SavedItem).delete()
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

        with self.assertLogs("app.assistant.loop", level="INFO") as logs:
            result = loop.run(self.db, self.user.id, "find me a Sunnyvale job")

        self.assertEqual(result.answer, "I found one Sunnyvale internship.")
        self.assertEqual(result.iterations, 2)
        self.assertEqual(result.tool_call_count, 1)
        self.assertFalse(result.reached_iteration_ceiling)
        self.assertEqual(result.tool_calls[0]["tool_name"], "search_jobs")
        self.assertEqual(len(fake_client.calls), 2)
        self.assertTrue(any("assistant_tool_call" in line for line in logs.output))
        self.assertTrue(any('"city": "Sunnyvale"' in line for line in logs.output))

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
        self.assertEqual(result.tool_call_count, 1)
        self.assertIn("tool-call limit", result.answer)

    def test_ollama_complete_keeps_chat_compatibility(self):
        client = OllamaClient(base_url="http://127.0.0.1:11434", model="test-model")
        expected = {"message": {"content": "ok"}}

        with patch.object(client, "chat", return_value=expected) as chat:
            result = client.complete([], tools=[])

        self.assertEqual(result, expected)
        chat.assert_called_once_with([], tools=[])

    def test_repair_reprompts_once_and_recovers(self):
        fake_client = FakeOllamaClient(
            [
                {
                    "message": {
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "malformed-call",
                                "function": {
                                    "name": "search_jobs",
                                    "arguments": "not valid json",
                                },
                            }
                        ],
                    }
                },
                {
                    "message": {
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "repaired-call",
                                "function": {
                                    "name": "search_jobs",
                                    "arguments": {"city": "Sunnyvale"},
                                },
                            }
                        ],
                    }
                },
                {"message": {"content": "I recovered and found the job."}},
            ]
        )

        result = AssistantLoop(client=fake_client).run(
            self.db,
            self.user.id,
            "find a Sunnyvale job",
        )

        self.assertEqual(result.repair_attempts, 1)
        self.assertTrue(result.repair_succeeded)
        self.assertEqual(result.tool_call_count, 2)
        self.assertEqual(len(fake_client.calls), 3)
        self.assertTrue(
            any(
                message.get("role") == "system"
                and "repair request" in message.get("content", "")
                for message in result.messages
            )
        )

    def test_repair_stops_after_one_attempt(self):
        repeated_error = {
            "message": {
                "content": "",
                "tool_calls": [
                    {
                        "id": "repeated-malformed-call",
                        "function": {
                            "name": "search_jobs",
                            "arguments": "not valid json",
                        },
                    }
                ],
            }
        }
        fake_client = FakeOllamaClient([repeated_error] * 5)

        result = AssistantLoop(client=fake_client).run(
            self.db,
            self.user.id,
            "keep trying",
        )

        repair_messages = [
            message
            for message in result.messages
            if message.get("role") == "system"
            and "repair request" in message.get("content", "")
        ]
        self.assertEqual(result.repair_attempts, 1)
        self.assertFalse(result.repair_succeeded)
        self.assertEqual(len(repair_messages), 1)
        self.assertTrue(result.reached_iteration_ceiling)
        self.assertEqual(result.failure_mode, "iteration_ceiling")
        self.assertEqual(result.tool_call_count, 5)

    def test_ollama_error_is_classified_and_stops(self):
        class FailingOllamaClient:
            def complete(self, messages, tools=None):
                raise OllamaError("simulated timeout")

        result = AssistantLoop(client=FailingOllamaClient()).run(
            self.db,
            self.user.id,
            "find a job",
        )

        self.assertEqual(result.failure_mode, "ollama_error")
        self.assertEqual(result.repair_attempts, 0)
        self.assertEqual(result.tool_call_count, 0)
        self.assertIn("simulated timeout", result.answer)

    def test_save_is_cancelled_without_confirmation(self):
        fake_client = FakeOllamaClient(
            [
                {
                    "message": {
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "save-call",
                                "function": {
                                    "name": "save_job_or_event",
                                    "arguments": {
                                        "item_type": "job",
                                        "item_id": self.job.id,
                                    },
                                },
                            }
                        ],
                    }
                },
                {"message": {"content": "I did not save it because confirmation was declined."}},
            ]
        )

        result = AssistantLoop(client=fake_client).run(
            self.db,
            self.user.id,
            "save this job",
        )

        self.assertIn("did not save", result.answer)
        self.assertEqual(result.tool_call_count, 1)
        self.assertTrue(result.tool_calls[0]["error"].startswith("cancelled:"))
        self.assertEqual(self.db.query(SavedItem).count(), 0)

    def test_save_runs_after_explicit_confirmation(self):
        fake_client = FakeOllamaClient(
            [
                {
                    "message": {
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "save-call-approved",
                                "function": {
                                    "name": "save_job_or_event",
                                    "arguments": {
                                        "item_type": "job",
                                        "item_id": self.job.id,
                                    },
                                },
                            }
                        ],
                    }
                },
                {"message": {"content": "The job was saved."}},
            ]
        )

        result = AssistantLoop(client=fake_client).run(
            self.db,
            self.user.id,
            "save this job",
            confirmed_save=True,
        )

        saved_result = json.loads(result.tool_calls[0]["result"])
        self.assertTrue(saved_result["saved"])
        self.assertEqual(self.db.query(SavedItem).count(), 1)


if __name__ == "__main__":
    # run the loop tests directly without requiring a separate test runner
    import unittest

    unittest.main()
