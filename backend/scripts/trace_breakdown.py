"""
Lab 2, Part 6 tracing evidence: where does the time go in an assistant request?

needs the backend running with Ollama. it sends 50 real assistant requests (one at a time, each in
a new conversation), reads the per-stage timing every response carries, and reports which stage
dominates: model inference, database queries, tool execution, memory store or queue wait.

    cd backend && source venv/bin/activate
    python -m scripts.trace_breakdown --base-url http://127.0.0.1:9160 --count 50

it also records one successful trace, one failed trace (a tool call that errors), and a Kafka trace
(/memory consolidate, whose event carries the same trace id into the memory worker's log).
about 50 model calls take 30-40 minutes on a laptop, so start it and leave it.

output: docs/trace_breakdown.json and docs/trace_breakdown.md
optional: --worker-log PATH  summarises "queue_wait_ms=" lines written by the Kafka workers.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
STAGES = ("model_inference", "database_queries", "tool_execution", "memory_store", "queue_wait", "other")

PROMPTS = [
    "Find data analyst jobs in Sunnyvale.",
    "Are there any career fairs or events I could attend in Cupertino?",
    "What do you know about my profile and preferences?",
    "Search for remote software engineer jobs.",
    "Which events in Mountain View are open to my major?",
    "Find part-time jobs in Cupertino that need SQL.",
    "Give me three tips for a career fair.",
    "Search for machine learning internships near Mountain View.",
    "Show me jobs that need Python in Sunnyvale.",
    "Find virtual events this month.",
]
FAILED_PROMPT = "Show me the details of job 999999."


def call(base: str, path: str, body: dict, token: str | None = None, trace_id: str | None = None,
         timeout: int = 400) -> dict:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if trace_id:
        headers["X-Trace-Id"] = trace_id
    request = urllib.request.Request(base + path, json.dumps(body).encode(), headers, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read())


class Session:
    """keep a login token and sign in again when it expires (a 50-request run outlives the token)."""

    def __init__(self, base: str, email: str, password: str):
        self.base, self.email, self.password = base, email, password
        self.token = ""
        self.login()

    def login(self) -> None:
        self.token = call(self.base, "/api/auth/login", {"email": self.email, "password": self.password})["access_token"]

    def chat(self, message: str, trace_id: str | None = None) -> dict:
        try:
            return call(self.base, "/api/assistant/chat", {"message": message}, self.token, trace_id)
        except urllib.error.HTTPError as error:
            if error.code != 401:
                raise
            self.login()
            return call(self.base, "/api/assistant/chat", {"message": message}, self.token, trace_id)


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(round(fraction * (len(ordered) - 1))))] if ordered else 0.0


def summarise(rows: list[dict]) -> dict:
    out = {}
    totals = [r["stage_timing_ms"]["total"] for r in rows]
    mean_total = statistics.mean(totals)
    for stage in STAGES + ("total",):
        values = [r["stage_timing_ms"].get(stage, 0.0) for r in rows]
        out[stage] = {"mean_ms": round(statistics.mean(values), 1), "median_ms": round(statistics.median(values), 1),
                      "p95_ms": round(percentile(values, 0.95), 1),
                      "share_of_total_pct": round(100 * statistics.mean(values) / mean_total, 1) if stage != "total" else 100.0}
    out["dominant_stage"] = max(STAGES, key=lambda s: out[s]["mean_ms"])
    return out


def queue_waits(path: str) -> dict | None:
    waits = [float(m) for m in re.findall(r"queue_wait_ms=([0-9.]+)", Path(path).read_text(errors="ignore"))]
    if not waits:
        return None
    return {"events": len(waits), "mean_ms": round(statistics.mean(waits), 1), "max_ms": round(max(waits), 1)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:9160")
    parser.add_argument("--email", default="student151@students.handshake-demo.com")
    parser.add_argument("--password", default="Password123!")
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--worker-log", default=None)
    parser.add_argument("--traces-only", action="store_true",
                        help="skip the batch of requests and only record the successful, failed and kafka traces")
    parser.add_argument("--out", default=str(REPO / "docs" / "trace_breakdown"))
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    session = Session(base, args.email, args.password)
    checkpoint = Path(args.out + ".partial.json")

    rows: list[dict] = []
    for number in range(1, 1 if args.traces_only else args.count + 1):
        prompt = PROMPTS[(number - 1) % len(PROMPTS)]
        started = time.time()
        try:
            reply = session.chat(prompt)
        except (urllib.error.URLError, TimeoutError) as error:
            print(f"{number:>2}/{args.count} request failed: {error}")
            continue
        timing = reply.get("stage_timing_ms")
        if not timing:
            print("the response has no stage_timing_ms: restart the backend so it runs the new code.")
            return 2
        rows.append({"n": number, "prompt": prompt, "trace_id": reply["trace_id"], "failure_mode": reply.get("failure_mode"),
                     "tool_calls": reply["tool_call_count"], "wall_s": round(time.time() - started, 1),
                     "stage_timing_ms": timing})
        checkpoint.write_text(json.dumps(rows))  # keep progress: a crash must not lose the run
        print(f"{number:>2}/{args.count} {timing['total'] / 1000:5.1f}s  model {timing['model_inference'] / 1000:5.1f}s  "
              f"db {timing['database_queries']:6.1f}ms  tools {timing['tool_execution']:6.1f}ms  {prompt[:40]}")

    if not rows and not args.traces_only:
        print("no successful requests")
        return 1

    summary = summarise(rows) if rows else None

    # one successful trace (the request closest to the median total that used a tool) with its spans
    with_tools = [r for r in rows if r["tool_calls"] and not r["failure_mode"]] or rows
    if with_tools:
        median_total = statistics.median(r["stage_timing_ms"]["total"] for r in with_tools)
        ok_prompt = min(with_tools, key=lambda r: abs(r["stage_timing_ms"]["total"] - median_total))["prompt"]
    else:
        ok_prompt = PROMPTS[0]
    ok_trace = session.chat(ok_prompt, trace_id=f"trace-ok-{uuid.uuid4().hex[:8]}")

    failed_trace = session.chat(FAILED_PROMPT, trace_id=f"trace-failed-{uuid.uuid4().hex[:8]}")

    kafka_trace_id = f"trace-kafka-{uuid.uuid4().hex[:8]}"
    kafka_reply = session.chat("/memory consolidate", trace_id=kafka_trace_id)

    def trace_view(reply: dict) -> dict:
        return {"trace_id": reply["trace_id"], "answer": reply["answer"][:300], "failure_mode": reply.get("failure_mode"),
                "tool_calls": [{"tool": t["tool_name"], "error": t.get("error")} for t in reply.get("tool_calls", [])],
                "stage_timing_ms": reply.get("stage_timing_ms"), "spans": reply.get("trace_spans")}

    report = {
        "requests": len(rows),
        "summary": summary,
        "successful_trace": trace_view(ok_trace),
        "failed_trace": trace_view(failed_trace),
        "kafka_trace": {"trace_id": kafka_trace_id, "answer": kafka_reply["answer"][:200],
                        "find_it_in_the_logs": f"grep {kafka_trace_id} loadtest/backend.log <worker log>"},
        "queue_wait": queue_waits(args.worker_log) if args.worker_log else None,
        "requests_detail": rows,
    }
    Path(args.out + ".json").write_text(json.dumps(report, indent=2))

    lines = [f"# Assistant traces ({len(rows)} batch requests)", ""]
    if summary:
        lines += ["| Stage | Mean (ms) | Median (ms) | p95 (ms) | Share of total |", "|---|---:|---:|---:|---:|"]
        for stage in STAGES + ("total",):
            s = summary[stage]
            lines.append(f"| {stage} | {s['mean_ms']} | {s['median_ms']} | {s['p95_ms']} | {s['share_of_total_pct']}% |")
        lines += ["", f"Dominant stage: **{summary['dominant_stage']}**.", ""]
    for title, key in (("Successful trace", "successful_trace"), ("Failed trace", "failed_trace")):
        view = report[key]
        lines += [f"## {title} `{view['trace_id']}`", "", f"failure_mode: {view['failure_mode']}; tool calls: {view['tool_calls']}", "",
                  "| Span | Start (ms) | Duration (ms) | Detail |", "|---|---:|---:|---|"]
        for span in sorted(view["spans"] or [], key=lambda x: x["start_ms"]):
            detail = ", ".join(f"{k}={v}" for k, v in span.items() if k not in ("stage", "start_ms", "ms"))
            lines.append(f"| {span['stage']} | {span['start_ms']} | {span['ms']} | {detail} |")
        lines.append("")
    Path(args.out + ".md").write_text("\n".join(lines))

    if summary:
        print(f"\ndominant stage: {summary['dominant_stage']} ({summary[summary['dominant_stage']]['share_of_total_pct']}% of mean time)")
    print(f"kafka trace id: {kafka_trace_id}  (grep it in the backend and worker logs)")
    print(f"wrote {args.out}.json and {args.out}.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
