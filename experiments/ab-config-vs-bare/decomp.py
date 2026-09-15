#!/usr/bin/env python3
"""Where the cost difference comes from: the prefix write on call 1 vs. everything after.

    python decomp.py [results.jsonl]

1. Recovers the prices Claude Code used by least squares on its own
   `total_cost_usd` against (input, 5m write, 1h write, cache read, output)
   summed per run. Residual should be ~0: the CLI's cost is exactly linear in
   those five counters. If it is not, the price sheet changed — trust the fit.
2. Splits each run into: first call (whose cache_creation is the prefix written
   for the new session) and the rest (calls 2..n). The prefix write is the part
   that amortises in a long session; the rest is what the configuration changes
   in how the model works.
3. Prints cost per run WITHOUT the first-call write, paired per (task, rep).

Needs the session transcripts still on disk (~/.claude/projects/...), because
per-call usage is only there; results.jsonl has per-run totals.
"""
import json
import os
import re
import statistics as st
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "results.jsonl")
R = [json.loads(l) for l in open(path, encoding="utf-8")]
ARMS = sorted({e["arm"] for e in R}, key=lambda a: a != "bare")
CLAUDE_DIR = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")


def find_transcript(sid):
    for root, _, files in os.walk(os.path.join(CLAUDE_DIR, "projects")):
        if sid + ".jsonl" in files:
            return os.path.join(root, sid + ".jsonl")
    return None


def calls(sid):
    p = find_transcript(sid)
    if not p:
        return []
    seen = set()
    out = []
    for l in open(p, encoding="utf-8", errors="replace"):
        try:
            e = json.loads(l)
        except ValueError:
            continue
        m = e.get("message") or {}
        u = m.get("usage")
        mid = m.get("id")
        if e.get("type") != "assistant" or not u or not mid or mid in seen:
            continue
        seen.add(mid)
        cc = u.get("cache_creation") or {}
        out.append(dict(inp=u.get("input_tokens", 0), cw=u.get("cache_creation_input_tokens", 0),
                        cr=u.get("cache_read_input_tokens", 0), out=u.get("output_tokens", 0),
                        cw5=cc.get("ephemeral_5m_input_tokens", 0), cw1=cc.get("ephemeral_1h_input_tokens", 0)))
    return out


def lstsq(X, y):
    """Ordinary least squares via normal equations (5 unknowns; stdlib only)."""
    n = len(X[0])
    A = [[sum(X[r][i] * X[r][j] for r in range(len(X))) for j in range(n)] for i in range(n)]
    b = [sum(X[r][i] * y[r] for r in range(len(X))) for i in range(n)]
    # drop all-zero columns (e.g. no 5m writes) so the system is not singular
    keep = [i for i in range(n) if any(X[r][i] for r in range(len(X)))]
    A = [[A[i][j] for j in keep] for i in keep]
    b = [b[i] for i in keep]
    m = len(keep)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for col in range(m):
        piv = max(range(col, m), key=lambda r: abs(M[r][col]))
        M[col], M[piv] = M[piv], M[col]
        for r in range(m):
            if r != col and M[col][col]:
                f = M[r][col] / M[col][col]
                M[r] = [a - f * c for a, c in zip(M[r], M[col])]
    sol = [0.0] * n
    for k, i in enumerate(keep):
        sol[i] = M[k][m] / M[k][k] if M[k][k] else 0.0
    return sol


X, y = [], []
for e in R:
    cs = calls(e["sid"])
    e["calls"] = cs
    if not cs:
        sys.exit(f"transcript for {e['sid']} not found under {CLAUDE_DIR}/projects — decomp needs the jsonl files")
    X.append([sum(c[k] for c in cs) for k in ("inp", "cw5", "cw1", "cr", "out")])
    y.append(e["cost_usd"])
p = lstsq(X, y)
resid = max(abs(sum(a * b for a, b in zip(row, p)) - yy) for row, yy in zip(X, y))
print("fitted prices US$/M: input %.2f  cw5m %.2f  cw1h %.2f  cache_read %.2f  output %.2f  (max residual %.4f)"
      % (*(v * 1e6 for v in p), resid))
print("cw5m total:", sum(r[1] for r in X), " cw1h total:", sum(r[2] for r in X))
P = dict(inp=p[0], cw5=p[1], cw1=p[2], cr=p[3], out=p[4])


def cost(c):
    return c["inp"] * P["inp"] + c["cw5"] * P["cw5"] + c["cw1"] * P["cw1"] + c["cr"] * P["cr"] + c["out"] * P["out"]


print("\n== decomposition per arm (mean per run) ==")
print(f"{'arm':7s} {'1st-call cw':>11s} {'cost 1st':>9s} {'cost rest':>10s} {'calls rest':>10s} "
      f"{'cost/call rest':>14s} {'cr/call':>9s} {'out/call':>9s}")
for arm in ARMS:
    g = [e for e in R if e["arm"] == arm]
    cw1 = [e["calls"][0]["cw"] for e in g]
    c1 = [cost(e["calls"][0]) for e in g]
    rest = [sum(cost(c) for c in e["calls"][1:]) for e in g]
    nrest = [len(e["calls"]) - 1 for e in g]
    allrest = [c for e in g for c in e["calls"][1:]]
    cpc = st.mean(cost(c) for c in allrest) if allrest else 0
    print(f"{arm:7s} {st.mean(cw1):11.0f} {st.mean(c1):9.3f} {st.mean(rest):10.3f} {st.mean(nrest):10.1f} "
          f"{cpc:14.4f} {st.mean(c['cr'] for c in allrest) if allrest else 0:9.0f} "
          f"{st.mean(c['out'] for c in allrest) if allrest else 0:9.0f}")
print("\n1st-call cache_creation per arm (min / median / max) — the prefix written for a new session:")
for arm in ARMS:
    v = [e["calls"][0]["cw"] for e in R if e["arm"] == arm]
    print(f"  {arm:7s} {min(v)} / {st.median(v):.0f} / {max(v)}")
print("\n== cost per run WITHOUT the first-call write (what amortises in a long session) ==")
for arm in ARMS:
    v = [e["cost_usd"] - e["calls"][0]["cw"] * P["cw1"] for e in R if e["arm"] == arm]
    print(f"  {arm:7s} mean {st.mean(v):.3f}  median {st.median(v):.3f}")
if len(ARMS) == 2:
    a, b = ARMS
    pairs = wins = 0
    for e in R:
        if e["arm"] != a:
            continue
        o = [x for x in R if x["task"] == e["task"] and x["rep"] == e["rep"] and x["arm"] == b]
        if not o:
            continue
        pairs += 1
        wins += (o[0]["cost_usd"] - o[0]["calls"][0]["cw"] * P["cw1"]) < (e["cost_usd"] - e["calls"][0]["cw"] * P["cw1"])
    print(f"  paired without prefix: {b} cheaper in {wins}/{pairs}")
