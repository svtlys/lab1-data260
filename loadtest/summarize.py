"""
turn the JMeter .jtl files into the numbers, table and graphs for the report.

    python summarize.py local            # reads results/local/*.jtl
    python summarize.py aws --ramp 30 --assistant-ramp 20

writes (in ../docs): loadtest_<label>.json, loadtest_<label>.md, loadtest_<label>_crud.png and
loadtest_<label>_assistant.png. samples from the ramp-up period are left out so the numbers describe
the full user load. percentiles use the nearest-rank method.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCS = HERE.parent / "docs"

# the request each plan is about (the sign-in request is not counted in the other plans)
PLAN_LABELS = {
    "login": "POST /api/auth/login",
    "job_search": "GET /api/jobs?search=",
    "apply": "POST /api/jobs/{id}/applications",
    "assistant": "POST /api/assistant/chat",
}
TITLES = {"login": "Login", "job_search": "Job search", "apply": "Application submission", "assistant": "AI assistant"}


def percentile(sorted_values: list[float], p: float) -> float:
    if not sorted_values:
        return float("nan")
    rank = max(1, math.ceil(p / 100 * len(sorted_values)))
    return sorted_values[rank - 1]


def summarize_file(path: Path, plan: str, ramp: int) -> dict | None:
    with path.open(newline="", encoding="utf-8") as handle:
        all_rows = list(csv.DictReader(handle))
    rows = [r for r in all_rows if r.get("label") == PLAN_LABELS[plan]]
    if not rows:
        return None
    logins = [r for r in all_rows if r.get("label") == PLAN_LABELS["login"]]
    login_failures = sum(1 for r in logins if r["success"].lower() != "true") if plan != "login" else 0
    start = min(int(r["timeStamp"]) for r in rows)
    steady = [r for r in rows if int(r["timeStamp"]) >= start + ramp * 1000] or rows
    elapsed = sorted(float(r["elapsed"]) for r in steady)
    first = min(int(r["timeStamp"]) for r in steady)
    last = max(int(r["timeStamp"]) + int(float(r["elapsed"])) for r in steady)
    seconds = max((last - first) / 1000, 1e-9)
    errors = sum(1 for r in steady if r["success"].lower() != "true")
    codes: dict[str, int] = {}
    for r in steady:
        codes[r["responseCode"]] = codes.get(r["responseCode"], 0) + 1
    users = int(re.search(r"_(\d+)\.jtl$", path.name).group(1))
    return {
        "plan": plan, "users": users, "samples": len(steady), "errors": errors,
        "error_rate_percent": round(100 * errors / len(steady), 2),
        "avg_ms": round(sum(elapsed) / len(elapsed), 1),
        "p50_ms": percentile(elapsed, 50), "p95_ms": percentile(elapsed, 95), "p99_ms": percentile(elapsed, 99),
        "max_ms": elapsed[-1], "throughput_per_s": round(len(steady) / seconds, 2),
        "response_codes": codes,
        "logins": len(logins) if plan != "login" else None, "login_failures": login_failures,
    }


def draw(results: list[dict], label: str) -> list[str]:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib is not installed; skipping graphs (pip install matplotlib)")
        return []
    written = []

    crud = [p for p in ("login", "job_search", "apply") if any(r["plan"] == p for r in results)]
    if crud:
        fig, (left, right) = plt.subplots(1, 2, figsize=(11, 4.2))
        for plan in crud:
            rows = sorted((r for r in results if r["plan"] == plan), key=lambda r: r["users"])
            left.plot([r["users"] for r in rows], [r["p95_ms"] for r in rows], marker="o", label=TITLES[plan])
            right.plot([r["users"] for r in rows], [r["throughput_per_s"] for r in rows], marker="o", label=TITLES[plan])
        left.set(title="95th percentile response time", xlabel="concurrent users", ylabel="milliseconds")
        right.set(title="Throughput", xlabel="concurrent users", ylabel="requests per second")
        for axis in (left, right):
            axis.grid(alpha=0.3)
            axis.legend()
        fig.suptitle(f"Pair 16 load test ({label}): login, job search, application submission")
        fig.tight_layout()
        path = DOCS / f"loadtest_{label}_crud.png"
        fig.savefig(path, dpi=160)
        written.append(str(path))
        plt.close(fig)

    rows = sorted((r for r in results if r["plan"] == "assistant"), key=lambda r: r["users"])
    if rows:
        fig, axis = plt.subplots(figsize=(6.5, 4.2))
        for key, name in (("p50_ms", "p50"), ("p95_ms", "p95"), ("p99_ms", "p99")):
            axis.plot([r["users"] for r in rows], [r[key] / 1000 for r in rows], marker="o", label=name)
        axis.set(title=f"AI assistant response time ({label})", xlabel="concurrent users", ylabel="seconds")
        axis.set_xticks([r["users"] for r in rows])
        axis.grid(alpha=0.3)
        axis.legend()
        fig.tight_layout()
        path = DOCS / f"loadtest_{label}_assistant.png"
        fig.savefig(path, dpi=160)
        written.append(str(path))
        plt.close(fig)
    return written


def failed(r: dict) -> str:
    return "n/a" if r.get("logins") is None else f"{r['login_failures']}/{r['logins']}"


def table(results: list[dict]) -> str:
    lines = ["| Scenario | Users | Samples | Error % | Failed logins | Avg ms | p50 ms | p95 ms | p99 ms | Max ms | Req/s |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    order = list(PLAN_LABELS)
    for r in sorted(results, key=lambda r: (order.index(r["plan"]), r["users"])):
        lines.append(f"| {TITLES[r['plan']]} | {r['users']} | {r['samples']} | {r['error_rate_percent']} | {failed(r)} | {r['avg_ms']} "
                     f"| {r['p50_ms']:.0f} | {r['p95_ms']:.0f} | {r['p99_ms']:.0f} | {r['max_ms']:.0f} | {r['throughput_per_s']} |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("label", help="results/<label> folder to read, for example local or aws")
    parser.add_argument("--ramp", type=int, default=30, help="ramp-up seconds to leave out (CRUD runs)")
    parser.add_argument("--assistant-ramp", type=int, default=20, help="ramp-up seconds to leave out (assistant runs)")
    args = parser.parse_args(argv)

    folder = HERE / "results" / args.label
    results = []
    for plan in PLAN_LABELS:
        for path in sorted(folder.glob(f"{plan}_*.jtl")):
            summary = summarize_file(path, plan, args.assistant_ramp if plan == "assistant" else args.ramp)
            if summary:
                results.append(summary)
    if not results:
        print(f"no results found in {folder}")
        return 1

    DOCS.mkdir(exist_ok=True)
    (DOCS / f"loadtest_{args.label}.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    md = table(results)
    (DOCS / f"loadtest_{args.label}.md").write_text(md + "\n", encoding="utf-8")
    print(md)
    for path in draw(results, args.label):
        print("wrote", path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
