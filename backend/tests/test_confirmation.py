"""
test the assistant confirmation gate without external services.
"""

from unittest import TestCase

from app.assistant.confirmation import confirm_action


class ConfirmationGateTests(TestCase):
    """verify read-only approval and explicit save confirmation."""

    def test_read_only_tools_do_not_require_confirmation(self):
        result = confirm_action("search_jobs", {"city": "Sunnyvale"})
        self.assertEqual(result, "approved")

    def test_save_requires_explicit_confirmation(self):
        result = confirm_action("save_job_or_event", {"item_type": "job", "item_id": 1})
        self.assertTrue(result.startswith("cancelled:"))

    def test_explicit_save_confirmation_approves_action(self):
        result = confirm_action(
            "save_job_or_event",
            {"item_type": "job", "item_id": 1},
            auto_approve=True,
        )
        self.assertEqual(result, "approved")


if __name__ == "__main__":
    import unittest

    unittest.main()
