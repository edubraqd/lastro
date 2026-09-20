#!/usr/bin/env python3
"""First call of every session: how much came from ANOTHER session's cache?

For each main-conversation JSONL under ~/.claude/projects (or
CLAUDE_CONFIG_DIR), takes the first assistant message with usage and measures
the gap to the last call of any other session in the same directory. A warm
start (< 60 min) that reads only the system-prompt layer means the CLAUDE.md
block was not shared (anthropics/claude-code#93499; our #94417 was closed as
a duplicate of it).

    python tools/first_call.py
"""
import bisect
import glob
import json
import os
import statistics
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import PROJECTS, ts  # noqa: E402


def scan(path):
    """(first call of the transcript or None, every main-thread call as (proj, ts, sid))."""
    proj = os.path.basename(os.path.dirname(path))
    first = None
    calls = []
    msg1 = 0  # chars rendered into the first user turn by attachments
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if '"usage"' not in line and '"attachment"' not in line:
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("type") == "attachment" and first is None:
                for b in r.get("rendered") or []:
                    if isinstance(b, dict):
                        msg1 += len(b.get("content", "") or "")
            if r.get("type") != "assistant" or r.get("isSidechain"):
                continue
            u = (r.get("message") or {}).get("usage")
            if not u or not r.get("timestamp"):
                continue
            t = ts(r["timestamp"])
            calls.append((proj, t, r.get("sessionId")))
            if first is None:
                first = dict(proj=proj, sid=r.get("sessionId"), t=t, ver=r.get("version"), ep=r.get("entrypoint"),
                             cr=u.get("cache_read_input_tokens", 0), cc=u.get("cache_creation_input_tokens", 0),
                             inp=u.get("input_tokens", 0), msg1=msg1)
    return first, calls


def main():
    rows, calls = [], []
    for f in glob.glob(os.path.join(PROJECTS, "*", "*.jsonl")):
        first, c = scan(f)
        calls.extend(c)
        if first:
            rows.append(first)
    calls.sort(key=lambda x: x[1])
    # one sorted list per project: scanning all ~330k calls per row cost ~15 s of a 31 s run
    by_proj = defaultdict(list)
    for c in calls:
        by_proj[c[0]].append(c)
    times = {p: [c[1] for c in cs] for p, cs in by_proj.items()}
    for r in rows:
        cs = by_proj[r["proj"]]
        i = bisect.bisect_left(times[r["proj"]], r["t"]) - 1   # last call strictly before this one
        while i >= 0 and cs[i][2] == r["sid"]:   # a resumed session can carry its own earlier calls in another file
            i -= 1
        r["gap_min"] = round((r["t"] - cs[i][1]).total_seconds() / 60) if i >= 0 else None
    rows.sort(key=lambda r: r["t"])
    print(f"{'date':16} {'project':28} {'ver':9} {'entry':8} {'gap':>6} {'cr':>7} {'cc':>7} {'msg1~tok':>8}")
    for r in rows[-45:]:
        print(f"{r['t'].astimezone().strftime('%m-%d %H:%M'):16} {r['proj'][:28]:28} {str(r['ver']):9} {str(r['ep'])[:8]:8} "
              f"{str(r['gap_min']):>6} {r['cr']:>7} {r['cc']:>7} {r['msg1'] // 4:>8}")
    # summary: warm (<60 min) vs cold, current versions only
    warm = [r for r in rows if r["gap_min"] is not None and r["gap_min"] < 60 and r["ver"] and r["ver"] >= "2.1.2"]
    cold = [r for r in rows if (r["gap_min"] is None or r["gap_min"] >= 60) and r["ver"] and r["ver"] >= "2.1.2"]
    for name, g in (("warm <60min", warm), ("cold >=60min", cold)):
        if g:
            print(name, "n=", len(g), "cr median", statistics.median(r["cr"] for r in g), "cr>0:", sum(r["cr"] > 0 for r in g),
                  "cr values:", sorted(set(r["cr"] for r in g))[-12:])


if __name__ == "__main__":
    main()
