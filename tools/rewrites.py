#!/usr/bin/env python3
"""Full re-writes with no idle gap: what sits between the two calls?

Looks at every pair of consecutive calls with gap < 60 min, same model, no
shrink, and flags the ones where cache_read collapsed to the shared prefix
(<= 60k) while cache_creation re-wrote > 20% of the context: the history was
intact but not reusable, so something *before* it changed. For each boundary
it records the non-message lines the transcript holds between the two calls
(attachments, mode changes, system events) and reports the re-write rate when
each is present, plus the rate by version and by previous-context size.

    python tools/rewrites.py              # everything (the 641-session figure below)
    python tools/rewrites.py --last 30    # the 30 most recent transcripts

Output of 2026-09-14 on 641 sessions is in report/findings.md §4.
"""
import argparse
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sessions import transcripts  # noqa: E402
from ledger import load, PREFIX_EVENTS  # noqa: E402
from _common import ts  # noqa: E402


def band(ctx):
    return "<200k" if ctx < 200000 else "200-500k" if ctx < 500000 else "500-800k" if ctx < 800000 else ">=800k"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project")
    ap.add_argument("--last", type=int, default=0, help="most recent N transcripts (0 = all)")
    ap.add_argument("--min-calls", type=int, default=5)
    args = ap.parse_args()

    seen = set()
    n_all = Counter(); n_broke = Counter()          # keyed by feature / version / band / turn kind
    unexplained = []
    for path in transcripts(args.project, args.last):
        calls = load(path, seen)
        if len(calls) < args.min_calls:
            continue
        sid = os.path.basename(path)[:8]
        for j in range(1, len(calls)):
            p, c = calls[j - 1], calls[j]
            pctx = p["input"] + p["cw"] + p["cr"]
            cctx = c["input"] + c["cw"] + c["cr"]
            if pctx < 20000 or not p["ts"] or not c["ts"]:
                continue
            gap = (ts(c["ts"]) - ts(p["ts"])).total_seconds() / 60
            if gap > 60 or p["model"] != c["model"] or "synthetic" in p["model"] or cctx < 0.7 * pctx:
                continue
            broke = c["cw"] > 0.2 * pctx and c["cw"] > 20000 and c["cr"] <= 60000
            feats = c["events"]
            keys = ["(all)", "turn:" + ("tool" if p["tool_turn"] else "user"), "ver:" + c["version"], "ctx:" + band(pctx)] + sorted(feats)
            for k in keys:
                n_all[k] += 1
                n_broke[k] += broke
            if broke and not (feats & PREFIX_EVENTS):
                unexplained.append((sid, c["version"], c["cw"], pctx))

    def show(prefix, min_n=20):
        rows = [(k, n_all[k], n_broke[k]) for k in n_all if k.startswith(prefix) and n_all[k] >= min_n]
        for k, n, b in sorted(rows, key=lambda r: -r[2]):
            print(f"  {k:45} n={n:7} re-wrote={b:5} {100 * b / n:5.1f}%")

    print(f"boundaries {n_all['(all)']:,}; full re-writes from the shared prefix {n_broke['(all)']:,} "
          f"({100 * n_broke['(all)'] / max(n_all['(all)'], 1):.1f}%)\n")
    print("by turn kind:"); show("turn:")
    print("\nby previous context:"); show("ctx:")
    print("\nby version:"); show("ver:", 500)
    print("\nby event present between the two calls (rate when present):"); show("attachment:"); show("system:"); show("mode"); show("custom-title")
    tok = sum(u[2] for u in unexplained)
    print(f"\nre-writes with no prefix-changing event between the calls: {len(unexplained)} ({tok:,} tokens)")
    print("  sessions holding them:", Counter(u[0] for u in unexplained).most_common(5))
    print("  by version:", Counter(u[1] for u in unexplained).most_common(6))


if __name__ == "__main__":
    main()
