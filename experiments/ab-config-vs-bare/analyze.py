#!/usr/bin/env python3
"""Per-arm and per-task summary of results.jsonl (+ judged.jsonl if present).

    python analyze.py [results.jsonl]

Accuracy: the oracle verdict, or the blind judge's for tasks without an oracle.
Cost: Claude Code's own total_cost_usd. Tokens: from the transcript, deduplicated.
Paired: for each (task, rep) pair, which arm was cheaper / shorter / fewer calls.
"""
import collections
import json
import os
import statistics as st
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "results.jsonl")
R = [json.loads(l) for l in open(path, encoding="utf-8")]
ARMS = sorted({e["arm"] for e in R}, key=lambda a: a != "bare")
judged = path.replace("results", "judged")
J = {}
if os.path.exists(judged):
    for l in open(judged, encoding="utf-8"):
        e = json.loads(l)
        v = e.get("judge") or e.get("juiz") or ""
        J[(e["task"], e["arm"], e["rep"])] = v.upper().startswith(("YES", "SIM"))
for e in R:
    k = (e["task"], e["arm"], e["rep"])
    e["acc"] = J[k] if e["ok"] is None and k in J else bool(e["ok"])
    u = e["jsonl"]
    e["ctx"] = u["input"] + u["cw"] + u["cr"]


def med(xs):
    return st.median(xs) if xs else float("nan")


print(f"runs: {len(R)}  errors: {sum(1 for e in R if e.get('err'))}")
print("\n== per arm (median | mean) ==")
print(f"{'arm':7s} {'n':>3s} {'acc':>5s} {'calls':>9s} {'ctx tok':>15s} {'cache read':>15s} {'cache write':>13s} "
      f"{'output':>11s} {'US$':>13s} {'sec':>11s} {'chars':>9s}")
for arm in ARMS:
    g = [e for e in R if e["arm"] == arm and not e.get("err")]

    def f(k):
        xs = [e[k] if k in e else e["jsonl"][k] for e in g]
        return f"{med(xs):.0f}|{st.mean(xs):.0f}"
    print(f"{arm:7s} {len(g):3d} {sum(e['acc'] for e in g)/len(g):5.0%} {f('calls'):>9s} {f('ctx'):>15s} "
          f"{f('cr'):>15s} {f('cw'):>13s} {f('output'):>11s} "
          f"{med([e['cost_usd'] for e in g]):.3f}|{st.mean([e['cost_usd'] for e in g]):.3f} {f('wall'):>11s} {f('chars'):>9s}")
print("\n== per task: acc/n  US$ mean  calls mean  ctx mean ==")
for t in sorted({e["task"] for e in R}):
    row = []
    for arm in ARMS:
        g = [e for e in R if e["task"] == t and e["arm"] == arm and not e.get("err")]
        if not g:
            row.append("-")
            continue
        row.append(f"{arm} {sum(e['acc'] for e in g)}/{len(g)} ${st.mean(e['cost_usd'] for e in g):.2f} "
                   f"{st.mean(e['jsonl']['calls'] for e in g):.1f}c {st.mean(e['ctx'] for e in g)/1000:.0f}k")
    print(f"{t:12s} " + "   ".join(f"{r:30s}" for r in row))
if len(ARMS) == 2:
    a, b = ARMS
    w = collections.Counter()
    for t in {e["task"] for e in R}:
        for rep in sorted({e["rep"] for e in R}):
            pa = [e for e in R if e["task"] == t and e["rep"] == rep and e["arm"] == a and not e.get("err")]
            pb = [e for e in R if e["task"] == t and e["rep"] == rep and e["arm"] == b and not e.get("err")]
            if pa and pb:
                w["pairs"] += 1
                w[f"{b}_cheaper"] += pb[0]["cost_usd"] < pa[0]["cost_usd"]
                w[f"{b}_shorter"] += pb[0]["chars"] < pa[0]["chars"]
                w[f"{b}_fewer_calls"] += pb[0]["jsonl"]["calls"] < pa[0]["jsonl"]["calls"]
    print("\npaired:", dict(w))
print("\n== failures ==")
for e in R:
    if not e["acc"] or e.get("err"):
        print(f"{e['task']} {e['arm']} r{e['rep']} err={e.get('err')} :: {(e.get('result') or '')[:160]!r}")
