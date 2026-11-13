"""
read-only MySQL-to-MongoDB migration planning for Pair 16.

summary and dry-run inspect MySQL counts and Mongo connectivity only. They do
not create collections or indexes and do not write to either database.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@dataclass(frozen=True)
class CollectionPlan:
    """describe one planned MongoDB collection."""

    collection: str
    source: str
    notes: str


COLLECTION_PLANS = (
    CollectionPlan("users", "users", "preserve integer public ids and bcrypt hashes"),
    CollectionPlan("sessions", "new Lab 2 collection", "TTL-backed session records"),
    CollectionPlan("student_profiles", "student_profiles", "unique user_id"),
    CollectionPlan("company_profiles", "company_profiles", "unique user_id"),
    CollectionPlan("jobs", "jobs", "preserve response-boundary employment normalization"),
    CollectionPlan("applications", "applications", "unique job_id and student_id"),
    CollectionPlan("resumes", "application resume files", "PDF bytes and metadata"),
    CollectionPlan("events", "events", "preserve eligibility and capacity fields"),
    CollectionPlan(
        "event_registrations",
        "event_registrations",
        "unique event_id and student_id",
    ),
    CollectionPlan("saved_items", "saved_items", "exactly one job_id or event_id"),
    CollectionPlan("activity_logs", "new Lab 2 collection", "audit and trace records"),
    CollectionPlan("assistant_rules", "new Lab 2 collection", "versioned assistant rules"),
    CollectionPlan("student_memory", "new Lab 2 collection", "student memory entries"),
    CollectionPlan(
        "conversations",
        "assistant_conversations, assistant_messages, assistant_tool_logs",
        "conversation documents with ordered messages and tool calls",
    ),
    CollectionPlan("processed_events", "new Lab 2 collection", "Kafka idempotency records"),
    CollectionPlan("counters", "new Lab 2 collection", "atomic numeric id allocation"),
)


INDEX_SPECS: dict[str, tuple[dict[str, Any], ...]] = {
    "users": (
        {"keys": {"email": 1}, "unique": True},
    ),
    "sessions": (
        {"keys": {"session_id": 1}, "unique": True},
        {"keys": {"user_id": 1}},
        {"keys": {"expires_at": 1}, "expireAfterSeconds": 0},
    ),
    "student_profiles": (
        {"keys": {"user_id": 1}, "unique": True},
    ),
    "company_profiles": (
        {"keys": {"user_id": 1}, "unique": True},
    ),
    "jobs": (
        {"keys": {"company_id": 1}},
        {"keys": {"city": 1, "posted_at": -1}},
        {"keys": {"employment_type": 1, "posted_at": -1}},
        {"keys": {"is_remote": 1, "posted_at": -1}},
    ),
    "applications": (
        {"keys": {"job_id": 1, "student_id": 1}, "unique": True},
        {"keys": {"student_id": 1, "applied_at": -1}},
        {"keys": {"job_id": 1, "status": 1}},
    ),
    "resumes": (
        {"keys": {"application_id": 1}, "unique": True},
    ),
    "events": (
        {"keys": {"company_id": 1}},
        {"keys": {"city": 1, "event_date": 1}},
        {"keys": {"event_type": 1, "event_date": 1}},
        {"keys": {"is_virtual": 1, "event_date": 1}},
    ),
    "event_registrations": (
        {"keys": {"event_id": 1, "student_id": 1}, "unique": True},
        {"keys": {"student_id": 1, "registered_at": -1}},
    ),
    "saved_items": (
        {
            "keys": {"student_id": 1, "job_id": 1},
            "unique": True,
            "partialFilterExpression": {"job_id": {"$exists": True}},
        },
        {
            "keys": {"student_id": 1, "event_id": 1},
            "unique": True,
            "partialFilterExpression": {"event_id": {"$exists": True}},
        },
    ),
    "activity_logs": (
        {"keys": {"user_id": 1, "occurred_at": -1}},
        {"keys": {"trace_id": 1}},
    ),
    "assistant_rules": (
        {"keys": {"rule_key": 1}, "unique": True},
        {"keys": {"enabled": 1, "version": -1}},
    ),
    "student_memory": (
        {"keys": {"student_id": 1, "date": -1}},
        {"keys": {"student_id": 1, "category": 1}},
    ),
    "conversations": (
        {"keys": {"student_id": 1, "updated_at": -1}},
    ),
    "processed_events": (
        {"keys": {"event_id": 1}, "unique": True},
        {"keys": {"processed_at": 1}},
    ),
    "counters": (
        {"keys": {"collection": 1}, "unique": True},
    ),
}


SOURCE_TABLES = (
    "users",
    "student_profiles",
    "company_profiles",
    "jobs",
    "applications",
    "events",
    "event_registrations",
    "saved_items",
    "assistant_conversations",
    "assistant_messages",
    "assistant_tool_logs",
)

COUNTER_COLLECTIONS = (
    "users",
    "student_profiles",
    "company_profiles",
    "jobs",
    "applications",
    "resumes",
    "events",
    "event_registrations",
    "saved_items",
    "conversations",
)

TARGET_COLLECTIONS = tuple(plan.collection for plan in COLLECTION_PLANS)

DIRECT_MAPPINGS = {
    "users": "users",
    "student_profiles": "student_profiles",
    "company_profiles": "company_profiles",
    "jobs": "jobs",
    "applications": "applications",
    "events": "events",
    "event_registrations": "event_registrations",
    "saved_items": "saved_items",
}


def _safe_error(error: Exception) -> str:
    """return an error without connection credentials."""

    detail = str(error)
    detail = re.sub(r"(mongodb(?:\+srv)?://)[^/@\s]+@", r"\1<redacted>@", detail)
    detail = re.sub(r"(?i)(password|secret|token|api[_-]?key)=([^,\s]+)", r"\1=<redacted>", detail)
    return detail


def _json_default(value: Any) -> str:
    """serialize common SQLAlchemy scalar values for planning output."""

    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return str(value)


def build_mongo_connection() -> tuple[str, str]:
    """build a Mongo URI from existing local development variable names."""

    database = os.getenv("MONGO_INITDB_DATABASE", "p16_handshake")
    uri = os.getenv("MONGO_URI")
    if uri:
        return uri, database

    username = os.getenv("MONGO_INITDB_ROOT_USERNAME")
    password = os.getenv("MONGO_INITDB_ROOT_PASSWORD")
    if not username or not password:
        raise RuntimeError(
            "MONGO_INITDB_ROOT_USERNAME and MONGO_INITDB_ROOT_PASSWORD are required"
        )

    host = os.getenv("MONGO_HOST", "127.0.0.1")
    port = os.getenv("MONGO_PORT", "27017")
    uri = (
        f"mongodb://{quote_plus(username)}:{quote_plus(password)}@"
        f"{host}:{port}/admin?authSource=admin"
    )
    return uri, database


def inspect_mongo() -> dict[str, Any]:
    """ping MongoDB without selecting or modifying a collection."""

    try:
        from pymongo import MongoClient

        uri, database = build_mongo_connection()
        client = MongoClient(uri, serverSelectionTimeoutMS=1500)
        result = client.admin.command("ping")
        client.close()
        return {
            "status": "connected" if result.get("ok") == 1 else "unhealthy",
            "database": database,
            "writes": 0,
        }
    except Exception as error:
        return {
            "status": "unavailable",
            "detail": _safe_error(error),
            "writes": 0,
        }


def open_mongo() -> tuple[Any, str]:
    """open and ping MongoDB for an explicitly selected operation."""

    from pymongo import MongoClient

    uri, database = build_mongo_connection()
    client = MongoClient(uri, serverSelectionTimeoutMS=3000)
    client.admin.command("ping")
    return client, database


def inspect_mysql() -> dict[str, Any]:
    """read source table counts and id ranges using SELECT statements only."""

    from sqlalchemy import inspect, text

    from app.core.database import engine

    counts: dict[str, dict[str, Any]] = {}
    with engine.connect() as connection:
        available_tables = set(inspect(engine).get_table_names())
        for table in SOURCE_TABLES:
            if table not in available_tables:
                counts[table] = {"status": "missing"}
                continue
            statement = text(
                f"SELECT COUNT(*) AS row_count, MIN(id) AS min_id, "
                f"MAX(id) AS max_id FROM `{table}`"
            )
            row = connection.execute(statement).mappings().one()
            counts[table] = {
                "status": "available",
                "count": int(row["row_count"]),
                "min_id": row["min_id"],
                "max_id": row["max_id"],
            }

        if "applications" in available_tables:
            resume_row = connection.execute(
                text(
                    "SELECT COUNT(*) AS row_count FROM applications "
                    "WHERE resume_path IS NOT NULL"
                )
            ).mappings().one()
            counts["application_resumes"] = {
                "status": "available",
                "count": int(resume_row["row_count"]),
            }

    return counts


def _normalize_value(value: Any) -> Any:
    """convert SQLAlchemy values into BSON-compatible values."""

    from enum import Enum

    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Decimal):
        from bson.decimal128 import Decimal128

        return Decimal128(str(value))
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    if isinstance(value, dict):
        return {key: _normalize_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_value(item) for item in value]
    return value


def _document_from_row(row: Any) -> dict[str, Any]:
    """convert one SQLAlchemy mapping into a Mongo document."""

    document = {key: _normalize_value(value) for key, value in dict(row).items()}
    if "id" in document:
        document["id"] = int(document["id"])
        document["_id"] = document["id"]
    return document


def load_source_documents() -> dict[str, list[dict[str, Any]]]:
    """load source rows using SELECT statements and no mutation."""

    from sqlalchemy import inspect, text

    from app.core.database import engine

    with engine.connect() as connection:
        available_tables = set(inspect(engine).get_table_names())
        missing = [table for table in SOURCE_TABLES if table not in available_tables]
        if missing:
            raise RuntimeError("required MySQL source tables are missing")

        rows: dict[str, list[dict[str, Any]]] = {}
        for table in SOURCE_TABLES:
            result = connection.execute(text(f"SELECT * FROM `{table}`"))
            rows[table] = [_document_from_row(row) for row in result.mappings()]
    return rows


def _resume_documents(applications: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """read existing PDF files for applications that reference a resume."""

    documents = []
    for application in applications:
        resume_path = application.get("resume_path")
        if not resume_path:
            continue
        path = Path(str(resume_path))
        if not path.is_file():
            raise RuntimeError("a referenced resume file is missing")
        content = path.read_bytes()
        resume_id = int(application["id"])
        documents.append(
            {
                "_id": resume_id,
                "id": resume_id,
                "application_id": int(application["id"]),
                "student_id": int(application["student_id"]),
                "job_id": int(application["job_id"]),
                "filename": application.get("resume_filename"),
                "content_type": "application/pdf",
                "size_bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
                "content": content,
            }
        )
    return documents


def _conversation_documents(
    conversations: list[dict[str, Any]],
    messages: list[dict[str, Any]],
    tool_logs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """embed ordered assistant messages and tool logs by conversation."""

    by_id = {
        int(row["id"]): {
            **row,
            "messages": [],
            "tool_calls": [],
        }
        for row in conversations
    }
    for message in messages:
        conversation = by_id.get(int(message["conversation_id"]))
        if conversation is not None:
            conversation["messages"].append(message)
    for tool_log in tool_logs:
        conversation = by_id.get(int(tool_log["conversation_id"]))
        if conversation is not None:
            conversation["tool_calls"].append(tool_log)
    for conversation in by_id.values():
        conversation["messages"].sort(key=lambda item: item["sequence_number"])
        conversation["tool_calls"].sort(key=lambda item: item["iteration"])
    return list(by_id.values())


def build_documents(source_rows: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    """build target documents while preserving public numeric identifiers."""

    documents = {
        target: [
            _document_from_row(row) if "id" in row else dict(row)
            for row in source_rows.get(source, [])
        ]
        for target, source in DIRECT_MAPPINGS.items()
    }
    documents["resumes"] = _resume_documents(source_rows["applications"])
    documents["conversations"] = _conversation_documents(
        source_rows["assistant_conversations"],
        source_rows["assistant_messages"],
        source_rows["assistant_tool_logs"],
    )
    for collection in TARGET_COLLECTIONS:
        documents.setdefault(collection, [])
    return documents


def ensure_collections_and_indexes(database: Any) -> None:
    """create the planned collections and indexes during --write only."""

    existing = set(database.list_collection_names())
    for collection_name in TARGET_COLLECTIONS:
        if collection_name not in existing:
            database.create_collection(collection_name)
        collection = database[collection_name]
        for number, specification in enumerate(INDEX_SPECS.get(collection_name, ())):
            keys = list(specification["keys"].items())
            options = {
                key: value
                for key, value in specification.items()
                if key != "keys"
            }
            options["name"] = f"{collection_name}_planned_{number}"
            collection.create_index(keys, **options)


def initialize_counters(database: Any, documents: dict[str, list[dict[str, Any]]]) -> int:
    """initialize counters without lowering an existing next id."""

    now = datetime.now(timezone.utc)
    counter_collection = database["counters"]
    writes = 0
    for collection_name in COUNTER_COLLECTIONS:
        maximum = max(
            (int(document["id"]) for document in documents.get(collection_name, []) if "id" in document),
            default=0,
        )
        counter_collection.update_one(
            {"_id": collection_name},
            {
                "$max": {"next_id": maximum + 1},
                "$set": {"collection": collection_name, "updated_at": now},
            },
            upsert=True,
        )
        writes += 1
    return writes


def write_migration(database: Any, documents: dict[str, list[dict[str, Any]]], allow_write: bool = False) -> dict[str, int]:
    """upsert documents and indexes only when --write is explicitly selected."""

    if not allow_write:
        raise RuntimeError("write migration requires --write")

    ensure_collections_and_indexes(database)
    counts: dict[str, int] = {}
    for collection_name, collection_documents in documents.items():
        collection = database[collection_name]
        count = 0
        for document in collection_documents:
            collection.replace_one({"_id": document["_id"]}, document, upsert=True)
            count += 1
        counts[collection_name] = count
    counts["counters"] = initialize_counters(database, documents)
    return counts


def verify_mongo(database: Any) -> dict[str, Any]:
    """inspect collection and index state without changing MongoDB."""

    existing = set(database.list_collection_names())
    result: dict[str, Any] = {}
    for collection_name in TARGET_COLLECTIONS:
        if collection_name not in existing:
            result[collection_name] = {"exists": False}
            continue
        result[collection_name] = {
            "exists": True,
            "count": database[collection_name].count_documents({}),
            "indexes": list(database[collection_name].index_information()),
        }
    return result


def planned_counts(source_counts: dict[str, dict[str, Any]]) -> dict[str, int | None]:
    """project source counts onto the planned target collections."""

    source_for_target = {
        "users": "users",
        "student_profiles": "student_profiles",
        "company_profiles": "company_profiles",
        "jobs": "jobs",
        "applications": "applications",
        "resumes": "application_resumes",
        "events": "events",
        "event_registrations": "event_registrations",
        "saved_items": "saved_items",
        "conversations": "assistant_conversations",
    }
    result: dict[str, int | None] = {}
    for target, source in source_for_target.items():
        result[target] = source_counts.get(source, {}).get("count")
    result["sessions"] = 0
    result["activity_logs"] = 0
    result["assistant_rules"] = 0
    result["student_memory"] = 0
    result["processed_events"] = 0
    result["counters"] = len(COUNTER_COLLECTIONS)
    return result


def print_report(mode: str, mysql: dict[str, Any], mongo: dict[str, Any]) -> None:
    """print a sanitized migration plan report."""

    print(f"migration mode: {mode}")
    print("mysql writes: 0")
    print("mongo writes: 0")
    print(f"mongo connectivity: {mongo['status']}")
    if mongo.get("detail"):
        print(f"mongo detail: {mongo['detail']}")

    print("planned source-to-collection mappings:")
    for plan in COLLECTION_PLANS:
        print(f"  {plan.collection} <- {plan.source} ({plan.notes})")

    if "error" in mysql:
        print(f"mysql connectivity: unavailable ({mysql['error']})")
        return

    print("mysql source counts and id ranges:")
    for source, details in mysql.items():
        if details.get("status") != "available":
            print(f"  {source}: {details.get('status', 'unknown')}")
            continue
        min_id = details.get("min_id")
        max_id = details.get("max_id")
        print(
            f"  {source}: count={details['count']} "
            f"id_range={min_id if min_id is not None else 'n/a'}.."
            f"{max_id if max_id is not None else 'n/a'}"
        )

    print("planned MongoDB document counts:")
    for collection, count in planned_counts(mysql).items():
        print(f"  {collection}: {count if count is not None else 'unavailable'}")

    print("required indexes:")
    for collection, indexes in INDEX_SPECS.items():
        print(f"  {collection}: {json.dumps(indexes, default=_json_default, sort_keys=True)}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """parse one non-writing planning mode."""

    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--summary", action="store_true")
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--write", action="store_true")
    modes.add_argument("--verify", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """run the read-only migration planning command."""

    args = parse_args(argv)
    if args.verify:
        try:
            client, database_name = open_mongo()
            try:
                result = verify_mongo(client[database_name])
            finally:
                client.close()
            print("verify mode: read-only")
            print(json.dumps(result, default=_json_default, sort_keys=True))
            return 0
        except Exception as error:
            print(f"verify failed: {_safe_error(error)}")
            return 1

    if args.write:
        try:
            source_rows = load_source_documents()
            documents = build_documents(source_rows)
            client, database_name = open_mongo()
            try:
                counts = write_migration(
                    client[database_name],
                    documents,
                    allow_write=True,
                )
            finally:
                client.close()
            print("migration mode: --write")
            print("mysql writes: 0")
            print(f"mongo upserts: {sum(counts.values())}")
            print(json.dumps(counts, sort_keys=True))
            return 0
        except Exception as error:
            print(f"write migration failed: {_safe_error(error)}")
            return 1

    mode = "--summary" if args.summary else "--dry-run"
    mongo = inspect_mongo()
    try:
        mysql = inspect_mysql()
    except Exception as error:
        mysql = {"error": _safe_error(error)}

    print_report(mode, mysql, mongo)
    return 0 if "error" not in mysql else 1


if __name__ == "__main__":
    raise SystemExit(main())
