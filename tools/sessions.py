#!/usr/bin/env python3
"""Per-session token usage from Claude Code transcripts, deduplicated.

Claude Code writes one `assistant` line per content block (thinking / text /
tool_use) and every line carries the same `usage`. Summing usage per line
overstates everything ~1.7x. This script dedups by (message.id, requestId),
which is what the API actually billed.

    python tools/sessions.py                    # every project, last 30 sessions
    python tools/sessions.py --project myrepo   # projects whose dir name contains "myrepo"
    python tools/sessions.py --last 100 --min-calls 5
    python tools/sessions.py --json > sessions.json

Columns: first-call cache_creation / cache_read (the prefix that was written vs.
served from a warm cache), totals per session, and the API-equivalent cost split
at Opus-class list prices (input 1x, cache read 0.1x, 1h cache write 2x, output 5x).
"""
import argparse
import glob
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import CLAUDE_DIR  # noqa: E402,F401  (also fixes stdout encoding)

# A resumed or forked session copies the whole transcript into a new file, so the
# same API calls appear in two files. This set is shared across every transcript
# read in one run; process files oldest-first so the original keeps its calls
# and the copy only counts what it added.
GLOBAL_SEEN = set()


def iter_calls(path, seen=None):
    """Yield one dict per API call (deduplicated) from a transcript."""
    if seen is None:
        seen = GLOBAL_SEEN
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if '"usage"' not in line:
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d.get("type") != "assistant":
                continue
            m = d.get("message") or {}
            u = m.get("usage")
            if not u:
                continue
            key = (m.get("id"), d.get("requestId"))
            if key in seen:
                continue
            seen.add(key)
            yield {
                "ts": d.get("timestamp", ""),
                "model": m.get("model", ""),
                "version": d.get("version", ""),
                "entrypoint": d.get("entrypoint", ""),
                "input": u.get("input_tokens") or 0,
                "cache_creation": u.get("cache_creation_input_tokens") or 0,
                "cache_read": u.get("cache_read_input_tokens") or 0,
                "output": u.get("output_tokens") or 0,
            }


def first_prompt(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d.get("type") != "user" or d.get("isMeta"):
                continue
            c = (d.get("message") or {}).get("content")
            if isinstance(c, str):
                return c[:60]
            if isinstance(c, list):
                for b in c:
                    if isinstance(b, dict) and b.get("type") == "text":
                        return b["text"][:60]
            return ""
    return ""


def transcripts(project_filter, last):
    paths = glob.glob(os.path.join(CLAUDE_DIR, "projects", "*", "*.jsonl"))
    if project_filter:
        paths = [p for p in paths if project_filter.lower() in os.path.basename(os.path.dirname(p)).lower()]
    paths.sort(key=os.path.getmtime, reverse=True)
    paths = paths[:last] if last else paths
    return sorted(paths, key=os.path.getmtime)


def summarize(path, min_calls):
    calls = list(iter_calls(path))
    if len(calls) < min_calls or not calls:
        return None
    tot = {k: sum(c[k] for c in calls) for k in ("input", "cache_creation", "cache_read", "output")}
    c0 = calls[0]
    return {
        "session": os.path.basename(path)[:-6],
        "project": os.path.basename(os.path.dirname(path)),
        "started": c0["ts"][:16],
        "entrypoint": c0["entrypoint"],
        "version": c0["version"],
        "model": c0["model"],
        "calls": len(calls),
        "first_cache_creation": c0["cache_creation"],
        "first_cache_read": c0["cache_read"],
        "context_median": int(statistics.median(c["input"] + c["cache_creation"] + c["cache_read"] for c in calls)),
        "prompt": first_prompt(path).replace("\n", " "),
        **tot,
    }


def cost(t):
    """API-equivalent dollars at $5/M input, Opus-class multipliers."""
    per_m = 5.0
    return {
        "cache_read": t["cache_read"] * 0.1 * per_m / 1e6,
        "cache_creation": t["cache_creation"] * 2.0 * per_m / 1e6,
        "output": t["output"] * 5.0 * per_m / 1e6,
        "input": t["input"] * per_m / 1e6,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", help="substring of the project dir name under ~/.claude/projects")
    ap.add_argument("--last", type=int, default=30, help="most recently modified N transcripts (0 = all)")
    ap.add_argument("--min-calls", type=int, default=1)
    ap.add_argument("--json", action="store_true", help="print one JSON object per session")
    args = ap.parse_args()

    rows = [r for r in (summarize(p, args.min_calls) for p in transcripts(args.project, args.last)) if r]
    if not rows:
        sys.exit("no transcripts found under " + os.path.join(CLAUDE_DIR, "projects"))

    if args.json:
        for r in rows:
            print(json.dumps(r, ensure_ascii=False))
        return

    rows.sort(key=lambda r: r["started"])
    print(f"{'started':16} {'session':8} {'calls':>5} {'1st cw':>7} {'1st cr':>7} {'ctx med':>8} {'cache_read':>12} {'cache_wr':>10} {'output':>8}  prompt")
    for r in rows:
        print(f"{r['started']:16} {r['session'][:8]:8} {r['calls']:5} {r['first_cache_creation']:7,} {r['first_cache_read']:7,} "
              f"{r['context_median']:8,} {r['cache_read']:12,} {r['cache_creation']:10,} {r['output']:8,}  {r['prompt'][:50]!r}")

    tot = {k: sum(r[k] for r in rows) for k in ("input", "cache_creation", "cache_read", "output")}
    c = cost(tot)
    total_cost = sum(c.values()) or 1
    print(f"\nsessions {len(rows)}; calls {sum(r['calls'] for r in rows):,}")
    print(f"first call: cache_creation median {int(statistics.median(r['first_cache_creation'] for r in rows)):,}; "
          f"cache_read median {int(statistics.median(r['first_cache_read'] for r in rows)):,}; "
          f"cold starts (cache_read=0): {sum(1 for r in rows if r['first_cache_read'] == 0)}/{len(rows)}")
    print("API-equivalent cost share (Opus list prices):")
    for k in ("cache_read", "cache_creation", "output", "input"):
        print(f"  {k:15} {tot[k]:15,} tok  ${c[k]:8.2f}  {100 * c[k] / total_cost:3.0f}%")


if __name__ == "__main__":
    main()
