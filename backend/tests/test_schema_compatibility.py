"""static checks for the additive lab 1 schema compatibility migration."""

import re
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "database" / "03_lab1_seed_compatibility.sql"
BASE_SCHEMA = ROOT / "database" / "02_schema.sql"


class SchemaCompatibilityTests(unittest.TestCase):
    """verify the migration is additive and targets the local lab database."""

    def test_migration_file_exists(self):
        self.assertTrue(MIGRATION.is_file())

    def test_migration_targets_required_columns_and_table(self):
        sql = MIGRATION.read_text(encoding="utf-8")
        for name in (
            "jobs",
            "company_id",
            "deadline",
            "applications",
            "job_id",
            "student_id",
            "status",
            "applied_at",
            "resume_filename",
            "resume_path",
        ):
            self.assertIn(name, sql)
        self.assertIn("p16_handshake", sql)
        self.assertIn("fk_jobs_company_profile", sql)
        self.assertIn("fk_application_job", sql)
        self.assertIn("fk_application_student", sql)
        self.assertIn("uq_app_job_student", sql)

    def test_migration_has_no_destructive_or_data_insert_statements(self):
        sql = MIGRATION.read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"(?im)^\s*(drop|truncate|delete|reset)\b", sql))
        self.assertIsNone(re.search(r"(?im)^\s*insert\s+into\b", sql))

    def test_migration_uses_additive_idempotent_guards(self):
        sql = MIGRATION.read_text(encoding="utf-8")
        self.assertGreaterEqual(sql.count("information_schema"), 4)
        self.assertIn("CREATE TABLE IF NOT EXISTS applications", sql)
        self.assertGreaterEqual(sql.count("PREPARE stmt FROM @sql"), 4)
        self.assertGreaterEqual(sql.count("DEALLOCATE PREPARE stmt"), 4)

    def test_base_schema_matches_head(self):
        current_schema = BASE_SCHEMA.read_text(encoding="utf-8").replace("\r\n", "\n")
        root_for_git = str(ROOT).replace("\\", "/")
        result = subprocess.run(
            [
                "git",
                "-c",
                f"safe.directory={root_for_git}",
                "show",
                "HEAD:database/02_schema.sql",
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
        )
        head_schema = result.stdout.decode("utf-8").replace("\r\n", "\n")
        self.assertEqual(current_schema, head_schema)


if __name__ == "__main__":
    unittest.main()
