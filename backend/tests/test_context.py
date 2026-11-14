"""
tests for token tracking, the 70% warning, compaction and trace ids (Lab 2, Part 6).
"""

import uuid
from unittest import TestCase

from app.assistant.context import (
    TokenTracker,
    clean_trace_id,
    compact_messages,
    estimate_tokens,
    new_trace_id,
    trace_uuid,
)


def long_text(label: str, words: int = 25) -> str:
    return f"{label}: " + "some filler words " * words


class TokenTrackerTests(TestCase):
    """verify token counting and the warning threshold."""

    def test_uses_counts_reported_by_the_model(self):
        tracker = TokenTracker(budget=1000)
        tracker.record({"prompt_eval_count": 400, "eval_count": 50}, [])
        self.assertEqual(tracker.snapshot()["total_tokens"], 450)
        self.assertFalse(tracker.snapshot()["estimated"])

    def test_estimates_when_the_model_reports_nothing(self):
        tracker = TokenTracker(budget=1000)
        tracker.record({"message": {"content": "x" * 400}}, [{"role": "user", "content": "y" * 800}])
        snapshot = tracker.snapshot()
        self.assertTrue(snapshot["estimated"])
        self.assertGreater(snapshot["prompt_tokens"], 150)

    def test_no_warning_at_exactly_70_percent(self):
        tracker = TokenTracker(budget=1000)
        tracker.record({"prompt_eval_count": 650, "eval_count": 50}, [])
        self.assertFalse(tracker.warning)

    def test_warning_above_70_percent(self):
        tracker = TokenTracker(budget=1000)
        tracker.record({"prompt_eval_count": 700, "eval_count": 10}, [])
        self.assertTrue(tracker.warning)
        self.assertTrue(tracker.snapshot()["warning"])

    def test_warning_stays_on_once_the_peak_was_over_70_percent(self):
        tracker = TokenTracker(budget=1000)
        tracker.record({"prompt_eval_count": 800, "eval_count": 10}, [])
        tracker.record({"prompt_eval_count": 100, "eval_count": 10}, [])
        self.assertTrue(tracker.warning)


class CompactionTests(TestCase):
    """verify compaction only shrinks the copy shown to the model."""

    def history(self, turns: int):
        messages = [{"role": "system", "content": "system prompt"}]
        for n in range(turns):
            messages.append({"role": "user", "content": long_text(f"question {n}")})
            messages.append({"role": "assistant", "content": long_text(f"answer {n}")})
        messages.append({"role": "user", "content": "current question"})
        return messages

    def test_nothing_changes_below_the_limit(self):
        messages = self.history(2)
        result, info = compact_messages(messages, budget=100000)
        self.assertIs(result, messages)
        self.assertFalse(info["compacted"])

    def test_old_history_is_summarised_and_recent_kept(self):
        messages = self.history(10)
        original = [dict(m) for m in messages]
        result, info = compact_messages(messages, budget=1500)

        self.assertTrue(info["compacted"])
        self.assertLess(info["tokens_after"], info["tokens_before"])
        self.assertEqual(result[0]["content"], "system prompt")
        self.assertIn("summary of the earlier conversation", result[1]["content"])
        self.assertEqual(result[-1]["content"], "current question")
        # the last four history messages survive word for word
        self.assertEqual(result[-5:-1], original[-5:-1])
        # the caller's list is untouched
        self.assertEqual(messages, original)

    def test_old_tool_results_are_truncated_but_the_newest_is_not(self):
        messages = [
            {"role": "system", "content": "system prompt"},
            {"role": "user", "content": "find jobs"},
            {"role": "assistant", "content": "", "tool_calls": [{"id": "1"}]},
            {"role": "tool", "tool_call_id": "1", "content": "A" * 6000},
            {"role": "assistant", "content": "", "tool_calls": [{"id": "2"}]},
            {"role": "tool", "tool_call_id": "2", "content": "B" * 600},
        ]
        result, info = compact_messages(messages, budget=1500)

        self.assertEqual(info["tool_results_truncated"], 1)
        self.assertIn("truncated", result[3]["content"])
        self.assertEqual(result[5]["content"], "B" * 600)

    def test_estimate_counts_tool_calls(self):
        plain = estimate_tokens([{"role": "assistant", "content": ""}])
        with_call = estimate_tokens(
            [{"role": "assistant", "content": "", "tool_calls": [{"function": {"name": "search_jobs"}}]}]
        )
        self.assertGreater(with_call, plain)


class TraceIdTests(TestCase):
    """verify trace ids are safe to put in logs."""

    def test_new_ids_are_uuids_and_different(self):
        first, second = new_trace_id(), new_trace_id()
        self.assertEqual(str(uuid.UUID(first)), first)
        self.assertNotEqual(first, second)

    def test_safe_value_is_kept(self):
        self.assertEqual(clean_trace_id("req-123.abc_9"), "req-123.abc_9")

    def test_unsafe_or_missing_values_are_replaced(self):
        for bad in (None, "", "has space", "line\nbreak", "x" * 65, 12345):
            cleaned = clean_trace_id(bad)
            self.assertNotEqual(cleaned, bad)
            self.assertEqual(str(uuid.UUID(cleaned)), cleaned)

    def test_any_safe_id_maps_to_a_stable_uuid(self):
        self.assertEqual(trace_uuid("demo-trace-1"), trace_uuid("demo-trace-1"))
        self.assertNotEqual(trace_uuid("demo-trace-1"), trace_uuid("demo-trace-2"))
        real = new_trace_id()
        self.assertEqual(str(trace_uuid(real)), real)
