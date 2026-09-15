#!/usr/bin/env python3
"""Classify prompt-cache breaks in Claude Code transcripts.

A "break" is a call whose cache_creation exceeds 20% of the previous call's
total context and 20k tokens: the history was re-written instead of read from
cache. Each break is classified by what can be observed in the log:

  ttl        gap to the previous call > 60 min (1h cache expired)
  prune      context shrank >= 30% with no gap (microcompact / tool-result
             clearing: cache_read collapses to the shared prefix, history
             re-written behind it)
  compact    a compact summary was written between the two calls
  resume     model id changed, or the previous call was a <synthetic> marker
  cold       cache_read == 0 with no gap (full miss)
  partial    none of the above (cache_read > 0, something after the prefix changed)

    python tools/breaks.py                  # last 30 transcripts, every project
    python tools/breaks.py --project myrepo --last 0
    python tools/breaks.py --top 20         # list the 20 largest breaks

Shares are computed against all cache_creation tokens in the same transcripts.
On the 30 sessions in report/cache-forensics.md, 36 breaks held 68% of all
cache writes.
"""
import argparse
import os
import statistics
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sessions import iter_calls, transcripts  # noqa: E402
from _common import ts  # noqa: E402

import json


def compact_timestamps(path):
    out = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if "isCompactSummary" not in line:
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d.get("isCompactSummary"):
                out.append(d.get("timestamp", ""))
    return out


def classify(prev, cur, compacts):
    gap_min = (ts(cur["ts"]) - ts(prev["ts"])).total_seconds() / 60 if cur["ts"] and prev["ts"] else -1
    prev_ctx = prev["input"] + prev["cache_creation"] + prev["cache_read"]
    cur_ctx = cur["input"] + cur["cache_creation"] + cur["cache_read"]
    if gap_min > 60:
        kind = "ttl"
    elif any(prev["ts"] <= c <= cur["ts"] for c in compacts):
        kind = "compact"
    elif "synthetic" in prev["model"] or (prev["model"] and cur["model"] and prev["model"] != cur["model"]):
        kind = "resume"
    elif cur_ctx < 0.7 * prev_ctx:
        kind = "prune"
    elif cur["cache_read"] == 0:
        kind = "cold"
    else:
        kind = "partial"
    return kind, gap_min, prev_ctx, cur_ctx


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project")
    ap.add_argument("--last", type=int, default=30, help="most recent N transcripts (0 = all)")
    ap.add_argument("--min-calls", type=int, default=5)
    ap.add_argument("--top", type=int, default=15, help="list the N largest breaks")
    args = ap.parse_args()

    kinds = Counter()
    kind_tok = Counter()
    breaks = []
    total_writes = 0
    n_calls = 0
    n_sessions = 0
    for path in transcripts(args.project, args.last):
        calls = list(iter_calls(path))
        if len(calls) < args.min_calls:
            continue
        n_sessions += 1
        n_calls += len(calls)
        total_writes += sum(c["cache_creation"] for c in calls)
        compacts = compact_timestamps(path)
        sid = os.path.basename(path)[:8]
        for i in range(1, len(calls)):
            prev, cur = calls[i - 1], calls[i]
            prev_ctx = prev["input"] + prev["cache_creation"] + prev["cache_read"]
            if not (cur["cache_creation"] > 0.2 * prev_ctx and cur["cache_creation"] > 20000):
                continue
            kind, gap, pctx, cctx = classify(prev, cur, compacts)
            kinds[kind] += 1
            kind_tok[kind] += cur["cache_creation"]
            breaks.append((cur["cache_creation"], sid, i, kind, gap, pctx, cctx, cur["cache_read"]))

    if not n_sessions:
        sys.exit("no transcripts with >= %d calls" % args.min_calls)

    print(f"sessions {n_sessions}; calls {n_calls:,}; cache_creation total {total_writes:,}\n")
    print(f"{'kind':8} {'n':>4} {'tokens written':>15} {'share of writes':>16}")
    for k in ("ttl", "prune", "compact", "resume", "cold", "partial"):
        if kinds[k]:
            print(f"{k:8} {kinds[k]:4} {kind_tok[k]:15,} {100 * kind_tok[k] / max(total_writes, 1):15.0f}%")
    brk_tok = sum(kind_tok.values())
    print(f"{'all':8} {sum(kinds.values()):4} {brk_tok:15,} {100 * brk_tok / max(total_writes, 1):15.0f}%")
    if breaks:
        print(f"\nre-write size: median {int(statistics.median(b[0] for b in breaks)):,}  max {max(b[0] for b in breaks):,}")
        print(f"\nlargest {args.top}:  written  session  call#  kind     gap   prev ctx -> ctx   cache_read")
        for w, sid, i, kind, gap, pctx, cctx, cr in sorted(breaks, reverse=True)[: args.top]:
            print(f"  {w:9,}  {sid}  #{i:<4} {kind:8} {gap:5.0f}m {pctx:9,} -> {cctx:9,}  {cr:9,}")


if __name__ == "__main__":
    main()
