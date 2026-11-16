"""
live evidence for Lab 2, Part 6 compaction: token counts before and after, and recall afterwards.

needs the backend running with Ollama (it makes real assistant calls, so it takes a few minutes):

    cd backend && source venv/bin/activate
    python -m scripts.compaction_demo --base-url http://127.0.0.1:9160

it signs in as a seeded demo student, has a short conversation about preferences, jobs and events,
runs /compact, then asks questions whose answers were only in the old history. an answer passes when
it contains the fact. results go to docs/compaction_results.json for the report.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def call(base: str, path: str, body: dict, token: str | None = None, timeout: int = 400) -> dict:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(base + path, json.dumps(body).encode(), headers, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:9160")
    parser.add_argument("--email", default="student150@students.handshake-demo.com")
    parser.add_argument("--password", default="Password123!")
    parser.add_argument("--out", default=str(REPO / "docs" / "compaction_results.json"))
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    token = call(base, "/api/auth/login", {"email": args.email, "password": args.password})["access_token"]
    conversation_id = None
    turns: list[dict] = []

    def chat(message: str) -> dict:
        nonlocal conversation_id
        started = time.time()
        reply = call(base, "/api/assistant/chat",
                     {"message": message, "conversation_id": conversation_id}, token)
        conversation_id = reply["conversation_id"]
        turns.append({"message": message, "seconds": round(time.time() - started, 1),
                      "tokens": reply.get("token_usage"), "answer": reply["answer"][:400]})
        print(f"> {message}\n  {reply['answer'][:200]!r}  ({turns[-1]['seconds']} s)")
        return reply

    chat("I want remote data analyst jobs near Sunnyvale. I know Python and SQL.")
    jobs_reply = chat("Search for data analyst jobs in Sunnyvale and list the first three.")
    chat("Are there any career fairs or events I could attend?")

    found = []
    for call_record in jobs_reply.get("tool_calls", []):
        if call_record["tool_name"] == "search_jobs" and isinstance(call_record.get("result"), list):
            found = call_record["result"]
    first_company = found[0]["company_name"] if found else None
    first_title = found[0]["title"] if found else None

    compact = chat("/compact")
    stored = (compact.get("compaction") or {}).get("stored", {})
    if not stored.get("compacted"):
        print("\nFAIL: /compact did not compact the stored history (is the backend running the new code? "
              "restart it). the recall questions below would prove nothing, so stopping.")
        return 2
    print(f"\ncompaction: {stored.get('messages_before')} messages / {stored.get('tokens_before')} tokens "
          f"-> {stored.get('messages_after')} message / {stored.get('tokens_after')} tokens")

    checks = [
        ("Which city did I say I wanted jobs in, and which skills did I list?", ["sunnyvale", "python"]),
    ]
    if first_company:
        checks.append(("What was the first job you found for me, and at which company?",
                       [first_company.lower()]))
    results = []
    for question, needles in checks:
        reply = chat(question)
        text = reply["answer"].lower()
        passed = all(needle in text for needle in needles)
        results.append({"question": question, "expected": needles, "answer": reply["answer"][:500], "passed": passed})
        print(f"  recall {'PASS' if passed else 'FAIL'} (expected {needles})")

    report = {
        "conversation_id": conversation_id,
        "first_job": {"title": first_title, "company": first_company},
        "compaction": stored,
        "recall": results,
        "all_recall_passed": all(r["passed"] for r in results),
        "turns": turns,
    }
    Path(args.out).write_text(json.dumps(report, indent=2))
    print(f"\nwrote {args.out}")
    return 0 if report["all_recall_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
