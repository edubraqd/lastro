#!/usr/bin/env python3
"""A/B of two launch routes (e.g. through a proxy vs. direct), per session.

Reads ~/.claude/.context-peaks.json (the `route` per session written by
hooks/context-guard.js: "proxy" when ANTHROPIC_BASE_URL points at loopback,
"direct" otherwise) and sums provider-reported usage from the transcripts
~/.claude/projects/*/<sid>.jsonl. Primary metric: input + cache_read +
cache_creation per call, i.e. what the API counted as context.

    python tools/ab-route.py                 # sessions since --since (default: today - 7d)
    python tools/ab-route.py --since 2026-09-14

n < 5 sessions per arm decides nothing; sessions of different length are not
comparable on totals, only on per-call medians.
"""
import argparse
import datetime as dt
import glob
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sessions import CLAUDE_DIR, iter_calls  # noqa: E402

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--since", default=(dt.date.today() - dt.timedelta(days=7)).isoformat())
args = ap.parse_args()

peaks_path = os.path.join(CLAUDE_DIR, ".context-peaks.json")
try:
    peaks = json.load(open(peaks_path, encoding="utf-8"))
except OSError:
    sys.exit(f"{peaks_path} not found: install hooks/context-guard.js first (hooks/install.py)")
route_of = {sid: p.get("route") for sid, p in peaks.items() if p.get("route") and p.get("last", "") >= args.since}

groups = {"direct": [], "proxy": []}
for path in glob.glob(os.path.join(CLAUDE_DIR, "projects", "*", "*.jsonl")):
    sid = os.path.basename(path)[:-6]
    route = route_of.get(sid)
    if not route:
        continue
    calls = [(c["input"] + c["cache_read"] + c["cache_creation"], c["cache_read"], c["output"])
             for c in iter_calls(path, seen=set())]
    if calls:
        groups.setdefault(route, []).append((sid, calls))

print(f"since {args.since}")
print(f"{'route':8s} {'sessions':>8s} {'calls':>8s} {'ctx/call median':>16s} {'ctx total':>13s} {'cache%':>7s} {'output/call':>12s}")
for route, sess in groups.items():
    calls = [c for _, cs in sess for c in cs]
    if not calls:
        print(f"{route:8s} {len(sess):8d} {0:8d}")
        continue
    ctx = [c[0] for c in calls]
    cr = sum(c[1] for c in calls)
    out = [c[2] for c in calls]
    print(f"{route:8s} {len(sess):8d} {len(calls):8d} {st.median(ctx):16.0f} {sum(ctx):13d} {100 * cr / sum(ctx):6.0f}% {st.median(out):12.0f}")
