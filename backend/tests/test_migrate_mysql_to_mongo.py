"""focused tests for the read-only migration planning scaffold."""

from contextlib import redirect_stdout
from io import StringIO
from unittest import TestCase
from unittest.mock import patch

from scripts.migrate_mysql_to_mongo import (
    COLLECTION_PLANS,
    INDEX_SPECS,
    build_documents,
    ensure_collections_and_indexes,
    main,
    planned_counts,
    write_migration,
)


class FakeCollection:
    def __init__(self):
        self.documents = {}
        self.indexes = []
        self.updates = []

    def create_index(self, keys, **options):
        self.indexes.append((keys, options))

    def replace_one(self, selector, document, upsert=False):
        self.documents[selector["_id"]] = dict(document)
        self.updates.append(("replace_one", selector, upsert))

    def update_one(self, selector, update, upsert=False):
        current = self.documents.setdefault(selector["_id"], {})
        current.update(update.get("$set", {}))
        for key, value in update.get("$max", {}).items():
            if key not in current or current[key] < value:
                current[key] = value
        self.updates.append(("update_one", selector, update, upsert))


class FakeDatabase:
    def __init__(self):
        self.collections = {}
        self.created_collections = []

    def list_collection_names(self):
        return list(self.collections)

    def create_collection(self, name):
        self.created_collections.append(name)
        self.collections[name] = FakeCollection()

    def __getitem__(self, name):
        return self.collections.setdefault(name, FakeCollection())


class MigrationPlanningTests(TestCase):
    """verify planning metadata without connecting to either database."""

    def test_required_collection_plan_is_complete(self):
        collections = {plan.collection for plan in COLLECTION_PLANS}
        self.assertEqual(
            collections,
            {
                "users",
                "sessions",
                "student_profiles",
                "company_profiles",
                "jobs",
                "applications",
                "resumes",
                "events",
                "event_registrations",
                "saved_items",
                "activity_logs",
                "assistant_rules",
                "student_memory",
                "conversations",
                "processed_events",
                "counters",
            },
        )

    def test_planned_counts_preserve_source_counts(self):
        source_counts = {
            "users": {"count": 4},
            "student_profiles": {"count": 3},
            "company_profiles": {"count": 1},
            "jobs": {"count": 6},
            "applications": {"count": 2},
            "application_resumes": {"count": 1},
            "events": {"count": 6},
            "event_registrations": {"count": 5},
            "saved_items": {"count": 2},
            "assistant_conversations": {"count": 7},
        }
        counts = planned_counts(source_counts)
        self.assertEqual(counts["users"], 4)
        self.assertEqual(counts["resumes"], 1)
        self.assertEqual(counts["conversations"], 7)
        self.assertEqual(counts["sessions"], 0)
        self.assertEqual(counts["counters"], 10)

    def test_required_indexes_include_session_ttl_and_uniqueness(self):
        session_indexes = INDEX_SPECS["sessions"]
        self.assertIn(
            {"keys": {"expires_at": 1}, "expireAfterSeconds": 0},
            session_indexes,
        )
        self.assertTrue(any(index.get("unique") for index in INDEX_SPECS["users"]))
        self.assertTrue(
            any(index.get("unique") for index in INDEX_SPECS["applications"])
        )

    def test_write_migration_refuses_without_explicit_write_gate(self):
        with self.assertRaisesRegex(RuntimeError, "requires --write"):
            write_migration(object(), {}, allow_write=False)

    def test_summary_does_not_call_write_path(self):
        output = StringIO()
        with (
            patch(
                "scripts.migrate_mysql_to_mongo.inspect_mongo",
                return_value={"status": "connected", "writes": 0},
            ),
            patch(
                "scripts.migrate_mysql_to_mongo.inspect_mysql",
                return_value={"users": {"count": 0, "status": "available"}},
            ),
            patch("scripts.migrate_mysql_to_mongo.write_migration") as write,
            redirect_stdout(output),
        ):
            self.assertEqual(main(["--summary"]), 0)
        write.assert_not_called()

    def test_build_documents_preserves_numeric_ids_and_is_repeatable(self):
        source = {
            "users": [{"id": 16, "email": "student@example.test"}],
            "student_profiles": [],
            "company_profiles": [],
            "jobs": [],
            "applications": [],
            "events": [],
            "event_registrations": [],
            "saved_items": [],
            "assistant_conversations": [],
            "assistant_messages": [],
            "assistant_tool_logs": [],
        }
        first = build_documents(source)
        second = build_documents(source)
        self.assertEqual(first, second)
        self.assertEqual(first["users"][0]["_id"], 16)
        self.assertEqual(first["users"][0]["id"], 16)

    def test_write_creates_collections_and_session_ttl_index(self):
        database = FakeDatabase()

        ensure_collections_and_indexes(database)

        self.assertEqual(
            set(database.created_collections),
            {plan.collection for plan in COLLECTION_PLANS},
        )
        session_indexes = database.collections["sessions"].indexes
        self.assertTrue(
            any(
                options.get("expireAfterSeconds") == 0
                and keys == [("expires_at", 1)]
                for keys, options in session_indexes
            )
        )

    def test_write_upserts_numeric_ids_and_initializes_counters(self):
        database = FakeDatabase()
        documents = {
            "users": [{"_id": 16, "id": 16, "email": "student@example.test"}],
            "jobs": [{"_id": 4, "id": 4, "title": "test"}],
        }

        first_counts = write_migration(database, documents, allow_write=True)
        first_user = database.collections["users"].documents[16]
        first_user_count = len(database.collections["users"].documents)
        second_counts = write_migration(database, documents, allow_write=True)

        self.assertEqual(first_counts["users"], 1)
        self.assertEqual(second_counts["users"], 1)
        self.assertEqual(first_user["id"], 16)
        self.assertEqual(len(database.collections["users"].documents), first_user_count)
        self.assertTrue(
            all(
                operation[0] == "replace_one" and operation[2] is True
                for operation in database.collections["users"].updates
            )
        )
        self.assertEqual(
            database.collections["counters"].documents["users"]["next_id"],
            17,
        )

    def test_verify_mode_is_read_only(self):
        database = FakeDatabase()
        database.create_collection("users")
        with patch(
            "scripts.migrate_mysql_to_mongo.open_mongo",
            return_value=(type("Client", (), {"__getitem__": lambda self, name: database, "close": lambda self: None})(), "p16_handshake"),
        ):
            with patch("scripts.migrate_mysql_to_mongo.verify_mongo", return_value={"users": {"exists": True}}) as verify:
                self.assertEqual(main(["--verify"]), 0)
                verify.assert_called_once_with(database)


if __name__ == "__main__":
    import unittest

    unittest.main()
