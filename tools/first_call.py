#!/usr/bin/env python3
"""First call of every session: how much came from ANOTHER session's cache?

For each main-conversation JSONL under ~/.claude/projects, takes the first
assistant message with usage and measures the gap to the last call of any
other session in the same directory. A warm start (< 60 min) that reads only
the system-prompt layer means the CLAUDE.md block was not shared
(anthropics/claude-code#94417).

    python tools/first_call.py
"""
import json, glob, os, sys
from datetime import datetime, timezone
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.expanduser("~/.claude/projects")
def ts(s): return datetime.fromisoformat(s.replace("Z","+00:00"))
rows=[]; calls=[]  # (cwd, ts) de toda chamada com usage
for f in glob.glob(ROOT+"/*/*.jsonl"):
    proj=os.path.basename(os.path.dirname(f)); first=None; n=0; env_len=0; msg1=0
    try:
        for line in open(f,encoding="utf-8",errors="replace"):
            if '"usage"' not in line and '"attachment"' not in line: continue
            try: r=json.loads(line)
            except: continue
            if r.get("type")=="attachment" and first is None:
                for b in r.get("rendered") or []:
                    if isinstance(b,dict): msg1+=len(b.get("content","") or "")
            if r.get("type")!="assistant" or r.get("isSidechain"): continue
            u=(r.get("message") or {}).get("usage")
            if not u: continue
            t=ts(r["timestamp"]); calls.append((proj,t,r.get("sessionId")))
            n+=1
            if first is None:
                first=dict(proj=proj,sid=r.get("sessionId"),t=t,ver=r.get("version"),ep=r.get("entrypoint"),
                           cr=u.get("cache_read_input_tokens",0),cc=u.get("cache_creation_input_tokens",0),
                           inp=u.get("input_tokens",0),msg1=msg1)
    except Exception as e: continue
    if first: rows.append(first)
calls.sort(key=lambda x:x[1])
for r in rows:
    prev=[c for c in calls if c[0]==r["proj"] and c[2]!=r["sid"] and c[1]<r["t"]]
    r["gap_min"]=round((r["t"]-prev[-1][1]).total_seconds()/60) if prev else None
rows.sort(key=lambda r:r["t"])
print(f"{'date':16} {'project':28} {'ver':9} {'entry':8} {'gap':>6} {'cr':>7} {'cc':>7} {'msg1~tok':>8}")
for r in rows[-45:]:
    print(f"{r['t'].astimezone().strftime('%m-%d %H:%M'):16} {r['proj'][:28]:28} {str(r['ver']):9} {str(r['ep'])[:8]:8} {str(r['gap_min']):>6} {r['cr']:>7} {r['cc']:>7} {r['msg1']//4:>8}")
# summary: warm (<60 min) vs cold
q=[r for r in rows if r["gap_min"] is not None and r["gap_min"]<60 and r["ver"] and r["ver"]>="2.1.2"]
f_=[r for r in rows if (r["gap_min"] is None or r["gap_min"]>=60) and r["ver"] and r["ver"]>="2.1.2"]
import statistics as st
for nome,g in (("warm <60min",q),("cold >=60min",f_)):
    if g: print(nome, "n=",len(g), "cr median", st.median([r['cr'] for r in g]), "cr>0:", sum(r['cr']>0 for r in g), "cr values:", sorted(set(r['cr'] for r in g))[-12:])
