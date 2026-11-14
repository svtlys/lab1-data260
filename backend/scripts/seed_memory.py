"""
load the memory consolidation seed and show the before/after (Lab 2, Part 3).

run from the backend folder:

    python -m scripts.seed_memory --dry-run                 # no database needed; prints the result
    python -m scripts.seed_memory --student-id 1            # load into Mongo (needs MONGO_READS_ENABLED=true)
    python -m scripts.seed_memory --student-id 1 --consolidate   # load, then consolidate directly
    python -m scripts.seed_memory --student-id 1 --kafka     # load, then send a memory.consolidate event

every run writes docs/memory_consolidation_results.json with the counts and every removed line.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from app.assistant.memory import InMemoryDatabase, consolidate_student, list_memories
from app.assistant.memory_seed import SEED_ROWS, seed_student_memory

DEFAULT_OUTPUT = Path(__file__).resolve().parents[2] / "docs" / "memory_consolidation_results.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="seed assistant memory and show consolidation")
    parser.add_argument("--student-id", type=int, default=1, help="user id of the student (default 1)")
    parser.add_argument("--dry-run", action="store_true", help="use an in-memory database instead of Mongo")
    parser.add_argument("--consolidate", action="store_true", help="consolidate right away (without Kafka)")
    parser.add_argument("--kafka", action="store_true", help="publish a memory.consolidate event instead")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    if args.dry_run:
        database = InMemoryDatabase()
        args.consolidate = True
    else:
        from app.core.mongo import get_mongo_database

        database = get_mongo_database()
        if database is None:
            print("Mongo is not enabled. Set MONGO_READS_ENABLED=true plus the Mongo settings, or use --dry-run.")
            return 2

    loaded = seed_student_memory(database, args.student_id)
    print(f"loaded {loaded} seed entries for student {args.student_id}")
    report = {
        "run_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "student_id": args.student_id,
        "seed_entries": len(SEED_ROWS),
        "mode": "dry-run" if args.dry_run else "mongo",
    }

    if args.kafka:
        from app.assistant.context import new_trace_id
        from app.assistant.memory import queue_consolidation

        outcome = queue_consolidation(database, args.student_id, new_trace_id())
        report["consolidation"] = outcome
        print(f"consolidation: {outcome['mode']}")
        if outcome["mode"] == "queued":
            print("event published; the memory worker will consolidate it (check activity_logs and /memory)")
    elif args.consolidate:
        summary = consolidate_student(database, args.student_id)
        report["consolidation"] = {k: v for k, v in summary.items() if k != "details"}
        report["removed_entries"] = summary["details"]
        report["remaining_entries"] = [
            {"date": e["date"], "category": e["category"], "text": e["text"]}
            for e in sorted(list_memories(database, args.student_id), key=lambda e: e["date"])
        ]
        print(f"before: {summary['before']}  after: {summary['after']}  "
              f"duplicates removed: {summary['duplicates']}  contradictions resolved: {summary['contradictions']}")
        for item in summary["details"]:
            if item["reason"] == "contradiction":
                print(f"  contradiction [{item['topic']}]: '{item['old_value']}' replaced by '{item['new_value']}'")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
