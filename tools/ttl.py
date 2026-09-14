#!/usr/bin/env python3
"""How often does an idle gap between two calls break the prompt cache?

For every pair of consecutive calls in a session, buckets the wall-clock gap
and counts how many of the second calls re-wrote the history (cache_creation
> 20% of the previous context and > 20k). This is the basis for the keep-alive
interval in tools/cache-proxy.py.

    python tools/ttl.py              # last 30 transcripts
    python tools/ttl.py --last 0     # everything
"""
import argparse
import os
import sys
from collections import Counter
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sessions import iter_calls, transcripts  # noqa: E402

BUCKETS = [(0, 2), (2, 5), (5, 10), (10, 20), (20, 30), (30, 45), (45, 60), (60, 90), (90, 180), (180, 1e9)]


def ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--project")
ap.add_argument("--last", type=int, default=30)
ap.add_argument("--min-calls", type=int, default=5)
args = ap.parse_args()

n = Counter()
broke = Counter()
for path in transcripts(args.project, args.last):
    calls = list(iter_calls(path))
    if len(calls) < args.min_calls:
        continue
    for i in range(1, len(calls)):
        prev, cur = calls[i - 1], calls[i]
        if not prev["ts"] or not cur["ts"]:
            continue
        gap = (ts(cur["ts"]) - ts(prev["ts"])).total_seconds() / 60
        prev_ctx = prev["input"] + prev["cache_creation"] + prev["cache_read"]
        if prev_ctx < 20000:
            continue
        for lo, hi in BUCKETS:
            if lo <= gap < hi:
                n[(lo, hi)] += 1
                if cur["cache_creation"] > 0.2 * prev_ctx and cur["cache_creation"] > 20000:
                    broke[(lo, hi)] += 1
                break

print(f"{'gap (min)':>10} {'pairs':>7} {'broke':>6} {'rate':>5}")
for b in BUCKETS:
    if n[b]:
        label = f"{b[0]:.0f}-{b[1]:.0f}" if b[1] < 1e9 else f">{b[0]:.0f}"
        print(f"{label:>10} {n[b]:7} {broke[b]:6} {100 * broke[b] / n[b]:4.0f}%")
