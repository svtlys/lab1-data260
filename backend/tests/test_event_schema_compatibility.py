"""static checks for the additive event schema migration."""

import hashlib
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "database" / "04_event_schema_compatibility.sql"
PREVIOUS_MIGRATION = ROOT / "database" / "03_lab1_seed_compatibility.sql"
PREVIOUS_MIGRATION_SHA256 = (
    "607502D6C64FDA268FC23BDCD7940663B82D673F794F4EFA9C26607D212D23B9"
)


class EventSchemaCompatibilityTests(unittest.TestCase):
    """verify the event migration is additive and idempotent."""

    def test_migration_file_exists(self):
        self.assertTrue(MIGRATION.is_file())

    def test_required_event_columns_and_types_are_present(self):
        sql = MIGRATION.read_text(encoding="utf-8")
        expected = (
            "company_id INT NULL",
            "eligible_majors VARCHAR(500) NULL",
            "min_cgpa DECIMAL(3,2) NULL",
            "min_grad_year INT NULL",
            "max_grad_year INT NULL",
            "eligibility_note VARCHAR(500) NULL",
        )
        for fragment in expected:
            self.assertIn(fragment, sql)
        self.assertIn("USE p16_handshake", sql)

    def test_company_index_and_foreign_key_are_present(self):
        sql = MIGRATION.read_text(encoding="utf-8")
        self.assertIn("idx_events_company_id", sql)
        self.assertIn("fk_events_company_profile", sql)
        self.assertIn("REFERENCES company_profiles(id)", sql)

    def test_migration_is_additive_and_has_no_data_changes(self):
        sql = MIGRATION.read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"(?im)^\s*(drop|truncate|delete|reset)\b", sql))
        self.assertIsNone(re.search(r"(?im)^\s*insert\s+into\b", sql))
        self.assertGreaterEqual(sql.count("information_schema"), 8)
        self.assertGreaterEqual(sql.count("PREPARE stmt FROM @sql"), 8)
        self.assertGreaterEqual(sql.count("DEALLOCATE PREPARE stmt"), 8)

    def test_previous_migration_is_unchanged(self):
        digest = hashlib.sha256(PREVIOUS_MIGRATION.read_bytes()).hexdigest().upper()
        self.assertEqual(digest, PREVIOUS_MIGRATION_SHA256)


if __name__ == "__main__":
    unittest.main()
