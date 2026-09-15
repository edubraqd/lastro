# Test issue claims against local transcripts. #84253: 1h TTL absent >=2.1.218? #91706: `cd` in Bash -> rewrite?
import json, os, re, sys
from collections import Counter, defaultdict
sys.path.insert(0, "D:/claude-context-forensics/tools")
from sessions import transcripts
from breaks import ts
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ttl = defaultdict(lambda: Counter())   # version -> {1h,5m} tokens (main only, non-sidechain)
n_all = Counter(); n_broke = Counter()
seen = set()
for path in transcripts(None, 0):
    lines = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for raw in f:
            try: lines.append(json.loads(raw))
            except ValueError: pass
    calls = []
    for i, d in enumerate(lines):
        if d.get("type") != "assistant": continue
        m = d.get("message") or {}; u = m.get("usage")
        if not u: continue
        key = (m.get("id"), d.get("requestId"))
        if key in seen: continue
        seen.add(key)
        cc = u.get("cache_creation") or {}
        v = d.get("version", "")
        if not d.get("isSidechain"):
            ttl[v]["1h"] += cc.get("ephemeral_1h_input_tokens") or 0
            ttl[v]["5m"] += cc.get("ephemeral_5m_input_tokens") or 0
            ttl[v]["calls"] += 1
        calls.append((i, d.get("timestamp",""), m.get("model",""), v,
                      (u.get("input_tokens") or 0)+(u.get("cache_creation_input_tokens") or 0)+(u.get("cache_read_input_tokens") or 0),
                      u.get("cache_creation_input_tokens") or 0, u.get("cache_read_input_tokens") or 0))
    if len(calls) < 5: continue
    for j in range(1, len(calls)):
        pi, pts, pm, _, pctx, _, _ = calls[j-1]
        ci, cts, cm, cv, cctx, cw, cr = calls[j]
        if pctx < 20000 or not pts or not cts: continue
        gap = (ts(cts)-ts(pts)).total_seconds()/60
        if gap > 60 or pm != cm or "synthetic" in pm or cctx < 0.7*pctx: continue
        broke = cw > 0.2*pctx and cw > 20000 and cr <= 60000
        blocks = ((lines[pi].get("message") or {}).get("content") or [])
        tools = [b for b in blocks if isinstance(b, dict) and b.get("type") == "tool_use"]
        if not tools: kind = "user-turn"
        else:
            bash = [b for b in tools if b.get("name") in ("Bash", "PowerShell")]
            cmds = " ".join(str((b.get("input") or {}).get("command","")) for b in bash)
            if bash and re.search(r"(^|[;&|]\s*)cd\s", cmds) and not re.search(r"\bcd\b[^;&|]*&&", cmds):
                kind = "bash:bare-cd"
            elif bash and re.search(r"(^|[;&|]\s*)cd\s", cmds):
                kind = "bash:cd&&"
            elif bash: kind = "bash:other"
            else: kind = "tool:" + tools[0].get("name","?")[:14]
        n_all[kind] += 1; n_broke[kind] += broke

print("# #84253: share of cache_creation requested as 1h, main thread, by version (calls>=200)")
for v in sorted(ttl, key=lambda x: [int(p) if p.isdigit() else 0 for p in x.split(".")]):
    c = ttl[v]; tot = c["1h"]+c["5m"]
    if c["calls"] >= 200 and tot:
        print(f"  {v:10} calls={c['calls']:6}  1h={100*c['1h']/tot:5.1f}%  5m={100*c['5m']/tot:5.1f}%")
print("\n# #91706: no-gap full re-write rate by what the previous assistant turn did (n>=30)")
for k, n in sorted(n_all.items(), key=lambda kv: -kv[1]):
    if n >= 30: print(f"  {k:18} n={n:6} re-wrote={n_broke[k]:4} {100*n_broke[k]/n:5.2f}%")
