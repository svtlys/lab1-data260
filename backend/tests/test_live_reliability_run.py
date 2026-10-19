"""test safe live-reliability configuration and evidence helpers."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from scripts.live_reliability_run_isolated import (
    EMAIL_ENV,
    TURNS,
    get_credentials,
    save_call_matches_approval,
    sanitize_records,
    sanitize_text,
    write_outputs,
)


class LiveReliabilitySafetyTests(TestCase):
    """verify that live evidence helpers do not expose or overwrite sensitive data."""

    def test_credentials_use_configured_email_and_hidden_password_prompt(self):
        prompts = []

        def password_prompt(prompt):
            prompts.append(prompt)
            return "test-only-password"

        email, password = get_credentials(
            environ={EMAIL_ENV: "dedicated@example.test"},
            password_fn=password_prompt,
        )

        self.assertEqual(email, "dedicated@example.test")
        self.assertEqual(password, "test-only-password")
        self.assertEqual(prompts, ["dedicated test student password: "])

    def test_credentials_require_an_email(self):
        with self.assertRaises(ValueError):
            get_credentials(environ={}, input_fn=lambda prompt: "", password_fn=lambda prompt: "unused")

    def test_sanitization_removes_credentials_tokens_emails_and_private_fields(self):
        jwt_value = "eyJheader.payload.signature"
        text = (
            f"email=student@example.test password=test-only-value token={jwt_value} "
            "student_id=42 phone=555-0100"
        )

        sanitized = sanitize_text(text)

        self.assertNotIn("student@example.test", sanitized)
        self.assertNotIn("test-only-value", sanitized)
        self.assertNotIn(jwt_value, sanitized)
        self.assertNotIn("555-0100", sanitized)
        self.assertNotIn("42", sanitized)

    def test_record_sanitization_preserves_turn_count(self):
        records = [
            {
                "id": 1,
                "prompt": "find a job",
                "note": "email=student@example.test",
                "answer": "token=eyJheader.payload.signature",
            }
        ]

        safe_records = sanitize_records(records)

        self.assertEqual(len(safe_records), len(records))
        self.assertNotIn("student@example.test", safe_records[0]["note"])
        self.assertNotIn("eyJheader.payload.signature", safe_records[0]["answer"])

    def test_evidence_refuses_to_overwrite_existing_directory(self):
        record = {
            "id": 1,
            "group": "read",
            "prompt": "find a job",
            "confirm_save": False,
            "http_status": 200,
            "tools_called": [],
            "iterations": 1,
            "repair_attempts": 0,
            "backend_failure_mode": None,
            "classification": "valid and correct",
            "note": "",
            "gate_outcome": "",
            "seconds": 0.1,
            "answer": "safe answer",
        }
        with TemporaryDirectory() as temporary_directory:
            output_dir = Path(temporary_directory) / "evidence"
            write_outputs([record], output_dir)
            with self.assertRaises(FileExistsError):
                write_outputs([record], output_dir)

    def test_save_confirmation_matches_only_the_approved_item(self):
        approved = {"item_type": "job", "item_id": 24}
        matching_call = {
            "tool_name": "save_job_or_event",
            "arguments": {"item_type": "job", "item_id": 24},
        }
        different_call = {
            "tool_name": "save_job_or_event",
            "arguments": {"item_type": "job", "item_id": 25},
        }

        self.assertTrue(save_call_matches_approval(matching_call, approved))
        self.assertFalse(save_call_matches_approval(different_call, approved))

    def test_all_26_turns_are_preserved(self):
        self.assertEqual(len(TURNS), 26)
        self.assertEqual(TURNS[-1][0], 26)


if __name__ == "__main__":
    import unittest

    unittest.main()
