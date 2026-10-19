"""
offline checks for deterministic seed generation.
"""

from unittest import TestCase

from scripts.generate_seed_data import (
    CITY_SET,
    N_APPLICATIONS,
    N_COMPANIES,
    N_EVENTS,
    N_JOBS,
    N_STUDENTS,
    SEED,
    check_integrity,
    generate,
    to_sql,
)


class SeedGeneratorTests(TestCase):
    """verify the generator without connecting to or changing MySQL."""

    @classmethod
    def setUpClass(cls):
        # generate one deterministic in-memory dataset for the assertions
        cls.data = generate()
        check_integrity(cls.data)

    def test_seed_and_required_counts(self):
        self.assertEqual(SEED, 16)
        self.assertEqual(len(self.data["student_profiles"]), N_STUDENTS)
        self.assertEqual(len(self.data["company_profiles"]), N_COMPANIES)
        self.assertEqual(len(self.data["jobs"]), N_JOBS)
        self.assertEqual(len(self.data["applications"]), N_APPLICATIONS)
        self.assertEqual(len(self.data["events"]), N_EVENTS)

    def test_all_generated_cities_use_pair_16_city_set(self):
        self.assertTrue(all(row["city"] in CITY_SET for row in self.data["student_profiles"]))
        self.assertTrue(all(row["location"] in CITY_SET for row in self.data["company_profiles"]))
        self.assertTrue(all(row["city"] in CITY_SET for row in self.data["jobs"]))
        self.assertTrue(all(row["city"] in CITY_SET for row in self.data["events"]))

    def test_duplicate_keys_are_prevented(self):
        self.assertEqual(
            len({row["email"] for row in self.data["users"]}),
            len(self.data["users"]),
        )
        self.assertEqual(
            len({row["company_name"] for row in self.data["company_profiles"]}),
            N_COMPANIES,
        )
        self.assertEqual(
            len({(row["job_id"], row["student_id"]) for row in self.data["applications"]}),
            N_APPLICATIONS,
        )
        self.assertEqual(
            len({(row["event_id"], row["student_id"]) for row in self.data["event_registrations"]}),
            len(self.data["event_registrations"]),
        )

    def test_default_sql_output_does_not_clear_tables(self):
        sql = to_sql(self.data)
        self.assertNotIn("DELETE FROM", sql)

    def test_same_seed_produces_same_data(self):
        self.assertEqual(self.data, generate(seed=16))


if __name__ == "__main__":
    import unittest

    unittest.main()
