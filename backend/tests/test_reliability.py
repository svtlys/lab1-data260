"""
test the bounded reliability experiment and repair results.
"""

from unittest import TestCase

from scripts.reliability_experiment import run_experiment


class ReliabilityExperimentTests(TestCase):
    """verify the 20-turn before-and-after classification counts."""

    def test_reliability_counts_and_repair_results(self):
        results = run_experiment()

        self.assertEqual(sum(results["before"].values()), 20)
        self.assertEqual(sum(results["after"].values()), 20)
        self.assertEqual(results["before"]["valid and correct tool calls"], 8)
        self.assertEqual(results["after"]["valid and correct tool calls"], 14)
        self.assertEqual(results["before"]["malformed arguments"], 3)
        self.assertEqual(results["after"]["malformed arguments"], 0)
        self.assertEqual(results["before"]["unknown tool names"], 2)
        self.assertEqual(results["after"]["unknown tool names"], 0)
        self.assertEqual(results["before"]["database errors"], 1)
        self.assertEqual(results["after"]["database errors"], 0)
        self.assertEqual(results["before"]["iteration-ceiling events"], 1)
        self.assertEqual(results["after"]["iteration-ceiling events"], 1)


if __name__ == "__main__":
    import unittest

    unittest.main()
