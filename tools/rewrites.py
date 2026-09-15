#!/usr/bin/env python3
"""Full re-writes with no idle gap: what sits between the two calls?

Looks at every pair of consecutive calls with gap < 60 min, same model, no
shrink, and flags the ones where cache_read collapsed to the shared prefix
(<= 60k) while cache_creation re-wrote > 20% of the context: the history was
intact but not reusable, so something *before* it changed. For each boundary
it records the non-message lines the transcript holds between the two calls
(attachments, mode changes, system events) and reports the re-write rate when
each is present, plus the rate by version and by previous-context size.

    python tools/rewrites.py --last 0

Output of 2026-09-14 on 641 sessions is in report/findings.md §4.
"""
import argparse
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sessions import transcripts  # noqa: E402
from _common import ts  # noqa: E402

# events that change the request prefix (tools, system prompt, params) — a
# re-write right after one of these has a visible cause
PREFIX_EVENTS = {
    "attachment:deferred_tools_delta", "attachment:mcp_instructions_delta", "attachment:skill_listing",
    "attachment:ultra_effort_enter", "system:model_refusal_fallback", "system:api_error",
    "attachment:dynamic_skill", "attachment:nested_memory", "attachment:directory", "attachment:file",
    "attachment:goal_status", "attachment:remote_session_change", "attachment:auto_mode",
    "permission-mode", "attachment:date_change",
}
SKIP = {"assistant", "user", "queue-operation", "last-prompt"}


def band(ctx):
    return "<200k" if ctx < 200000 else "200-500k" if ctx < 500000 else "500-800k" if ctx < 800000 else ">=800k"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project")
    ap.add_argument("--last", type=int, default=30)
    ap.add_argument("--min-calls", type=int, default=5)
    args = ap.parse_args()

    seen = set()
    n_all = Counter(); n_broke = Counter()          # keyed by feature / version / band / turn kind
    unexplained = []
    for path in transcripts(args.project, args.last):
        lines = []
        with open(path, encoding="utf-8", errors="replace") as f:
            for raw in f:
                try:
                    lines.append(json.loads(raw))
                except ValueError:
                    pass
        calls = []
        for i, d in enumerate(lines):
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
            calls.append((i, d.get("timestamp", ""), m.get("model", ""), d.get("version", ""),
                          (u.get("input_tokens") or 0) + (u.get("cache_creation_input_tokens") or 0) + (u.get("cache_read_input_tokens") or 0),
                          u.get("cache_creation_input_tokens") or 0, u.get("cache_read_input_tokens") or 0))
        if len(calls) < args.min_calls:
            continue
        sid = os.path.basename(path)[:8]
        for j in range(1, len(calls)):
            pi, pts, pm, _, pctx, _, _ = calls[j - 1]
            ci, cts, cm, cv, cctx, cw, cr = calls[j]
            if pctx < 20000 or not pts or not cts:
                continue
            gap = (ts(cts) - ts(pts)).total_seconds() / 60
            if gap > 60 or pm != cm or "synthetic" in pm or cctx < 0.7 * pctx:
                continue
            broke = cw > 0.2 * pctx and cw > 20000 and cr <= 60000
            feats = set()
            for d in lines[pi + 1:ci]:
                t = d.get("type")
                if t in SKIP:
                    continue
                feats.add(t)
                if t == "system":
                    feats.add("system:" + str(d.get("subtype")))
                if t == "attachment":
                    feats.add("attachment:" + str((d.get("attachment") or {}).get("type")))
            prev_tool = any(isinstance(b, dict) and b.get("type") == "tool_use"
                            for b in ((lines[pi].get("message") or {}).get("content") or []))
            keys = ["(all)", "turn:" + ("tool" if prev_tool else "user"), "ver:" + cv, "ctx:" + band(pctx)] + sorted(feats)
            for k in keys:
                n_all[k] += 1
                n_broke[k] += broke
            if broke and not (feats & PREFIX_EVENTS):
                unexplained.append((sid, cv, cw, pctx))

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
