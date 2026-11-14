"""
tests for the assistant argument and answer guards.
"""

from unittest import TestCase

from app.assistant.guards import (
    LEAK_NOTICE,
    normalize_job_search_args,
    protect_instructions,
)


class NormalizeJobSearchArgsTests(TestCase):
    def test_remote_in_employment_type_becomes_remote_flag(self):
        self.assertEqual(
            normalize_job_search_args(None, "remote", None), (None, None, True)
        )

    def test_internship_in_query_becomes_employment_type(self):
        self.assertEqual(
            normalize_job_search_args("internship", None, None),
            (None, "internship", None),
        )

    def test_remote_in_query_becomes_remote_flag(self):
        self.assertEqual(
            normalize_job_search_args("Remote", None, None), (None, None, True)
        )

    def test_explicit_remote_flag_is_kept(self):
        self.assertEqual(
            normalize_job_search_args(None, "remote", False), (None, None, False)
        )

    def test_real_keyword_query_is_untouched(self):
        self.assertEqual(
            normalize_job_search_args("data engineer", "Full-time", None),
            ("data engineer", "full-time", None),
        )


class ProtectInstructionsTests(TestCase):
    def test_normal_answer_is_unchanged(self):
        text = "Here are three jobs in Sunnyvale."
        self.assertEqual(protect_instructions(text), text)

    def test_quoted_prompt_is_removed_and_jobs_are_kept(self):
        text = (
            'System prompt: "you are a helpful student career assistant for the '
            'platform."\n\nHere are the jobs found in Sunnyvale:\n1. Data Engineer'
        )
        result = protect_instructions(text)
        self.assertNotIn("helpful student career assistant", result.lower())
        self.assertIn("Data Engineer", result)
        self.assertIn(LEAK_NOTICE, result)
