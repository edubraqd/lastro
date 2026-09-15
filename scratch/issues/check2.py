# computer-use turns: which tool, did the result carry an image, how many tokens rewritten
import json, sys
from collections import Counter, defaultdict
sys.path.insert(0, "D:/claude-context-forensics/tools")
from sessions import transcripts
from breaks import ts
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
n_all=Counter(); n_broke=Counter(); tok=Counter(); sess=defaultdict(set); ver=Counter()
seen=set(); tot_unexpl_tok=0; tot_unexpl=0
for path in transcripts(None, 0):
    lines=[]
    with open(path, encoding="utf-8", errors="replace") as f:
        for raw in f:
            try: lines.append(json.loads(raw))
            except ValueError: pass
    calls=[]
    for i,d in enumerate(lines):
        if d.get("type")!="assistant": continue
        m=d.get("message") or {}; u=m.get("usage")
        if not u: continue
        key=(m.get("id"), d.get("requestId"))
        if key in seen: continue
        seen.add(key)
        calls.append((i,d.get("timestamp",""),m.get("model",""),d.get("version",""),
            (u.get("input_tokens") or 0)+(u.get("cache_creation_input_tokens") or 0)+(u.get("cache_read_input_tokens") or 0),
            u.get("cache_creation_input_tokens") or 0,u.get("cache_read_input_tokens") or 0))
    if len(calls)<5: continue
    sid=path.split("\\")[-1][:8]
    for j in range(1,len(calls)):
        pi,pts,pm,_,pctx,_,_=calls[j-1]; ci,cts,cm,cv,cctx,cw,cr=calls[j]
        if pctx<20000 or not pts or not cts: continue
        gap=(ts(cts)-ts(pts)).total_seconds()/60
        if gap>60 or pm!=cm or "synthetic" in pm or cctx<0.7*pctx: continue
        broke=cw>0.2*pctx and cw>20000 and cr<=60000
        if broke: tot_unexpl+=1; tot_unexpl_tok+=cw
        blocks=((lines[pi].get("message") or {}).get("content") or [])
        tools=[b for b in blocks if isinstance(b,dict) and b.get("type")=="tool_use"]
        if not tools or not tools[0].get("name","").startswith("mcp__computer-use"): continue
        name=tools[0]["name"].replace("mcp__computer-use__","")
        # did the tool_result between the calls carry an image?
        img=False
        for d in lines[pi+1:ci]:
            for b in ((d.get("message") or {}).get("content") or []):
                if isinstance(b,dict) and b.get("type")=="tool_result":
                    for c in (b.get("content") or []) if isinstance(b.get("content"),list) else []:
                        if isinstance(c,dict) and c.get("type")=="image": img=True
        k=f"{name}:{'img' if img else 'noimg'}"
        n_all[k]+=1; n_broke[k]+=broke
        if broke: tok[k]+=cw; sess[k].add(sid); ver[cv]+=1
print(f"all no-gap full re-writes: {tot_unexpl} ({tot_unexpl_tok:,} tok)\n")
for k,n in sorted(n_all.items(), key=lambda kv:-kv[1]):
    if n>=10: print(f"  {k:28} n={n:5} re-wrote={n_broke[k]:3} {100*n_broke[k]/n:5.1f}%  tok={tok[k]:>11,}  sessions={len(sess[k])}")
print("\nre-writes after computer-use, by version:", ver.most_common(8))
