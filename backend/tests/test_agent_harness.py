import unittest

from scripts.agent_harness import build_cases, run_all


EXPECTED_CASES = {
    "read_only_search",
    "accepted_save",
    "declined_save",
    "malformed_arguments_repair",
    "unknown_tool",
    "no_match_search",
    "history_followup",
    "injection_in_database_content",
    "system_prompt_leak",
    "iteration_ceiling",
    "repair_limit",
    "model_unavailable",
    "remote_filter_normalisation",
    "token_use_below_warning",
    "token_warning_above_70_percent",
    "compaction_near_window_limit",
    "trace_id_supplied_by_caller",
    "trace_id_unsafe_replaced",
    "memory_in_system_prompt",
    "injection_in_memory",
}


class AgentHarnessTests(unittest.TestCase):
    def test_expected_cases_are_defined_once(self):
        cases = build_cases()
        names = [case.name for case in cases]
        self.assertEqual(len(names), len(EXPECTED_CASES))
        self.assertEqual(set(names), EXPECTED_CASES)
        self.assertEqual(len(names), len(set(names)))

    def test_run_all_uses_production_assistant_path(self):
        report = run_all()
        self.assertEqual(report["summary"], {"total": 20, "passed": 20, "failed": 0})
        self.assertEqual(len(report["cases"]), 20)
        self.assertTrue(all(case["passed"] for case in report["cases"]))


if __name__ == "__main__":
    unittest.main()
