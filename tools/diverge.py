#!/usr/bin/env python3
"""Where did two consecutive requests diverge? Cross a cache break with the bodies.

Reads ~/.claude/cache-proxy.log (written by tools/cache-proxy.py) and, for
every call whose cache_creation re-wrote > 20% of the previous context, loads
the saved bodies of that call and the one before (cache-proxy-bodies/, needs
CACHE_PROXY_KEEP_BODIES > 0) and walks them in prompt-cache order — tools,
then system blocks, then messages — reporting the first element that differs
and a short excerpt around the first differing character.

    python tools/diverge.py               # every break in the log
    python tools/diverge.py --all         # every consecutive pair, break or not
    python tools/diverge.py A.json B.json # two explicit bodies

What the report means: the prefix cached by the API is byte-exact up to the
first difference. If the first difference is inside `system[3]` (the
project block) or `messages[0]`, the whole history behind it was re-written;
if it is at the last message, that is the normal per-turn write.
"""
import argparse
import glob
import json
import os
import sys

HOME = os.path.expanduser("~")
LOG = os.path.join(HOME, ".claude", "cache-proxy.log")
BODIES = os.path.join(HOME, ".claude", "cache-proxy-bodies")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def canon(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True)


def first_diff(a, b):
    n = min(len(a), len(b))
    for i in range(n):
        if a[i] != b[i]:
            return i
    return n if len(a) != len(b) else -1


def excerpt(a, b, i, w=120):
    return ("      before: …" + a[max(0, i - w):i + w].replace("\n", "\\n") + "…\n"
            "      after : …" + b[max(0, i - w):i + w].replace("\n", "\\n") + "…")


def sequence(body):
    """The request in cache order: one (label, canonical text) per element."""
    seq = []
    for i, t in enumerate(body.get("tools") or []):
        seq.append((f"tools[{i}] {t.get('name', '')}", canon(t)))
    sysb = body.get("system")
    if isinstance(sysb, str):
        seq.append(("system", sysb))
    else:
        for i, blk in enumerate(sysb or []):
            seq.append((f"system[{i}] {'cache' if blk.get('cache_control') else ''}", canon(blk)))
    for i, m in enumerate(body.get("messages") or []):
        seq.append((f"messages[{i}] {m.get('role')}", canon(m)))
    return seq


def compare(prev, cur, label=""):
    ps, cs = sequence(prev), sequence(cur)
    for k in ("model", "max_tokens", "thinking", "output_config", "context_management", "metadata"):
        if canon(prev.get(k)) != canon(cur.get(k)):
            print(f"  param `{k}` changed: {canon(prev.get(k))[:100]} -> {canon(cur.get(k))[:100]}")
    for i, ((pl, pt), (cl, ct)) in enumerate(zip(ps, cs)):
        if pt != ct:
            j = first_diff(pt, ct)
            print(f"  first differing element: #{i} {pl!r} (prev) vs {cl!r} (cur), at char {j} of {len(pt)}/{len(ct)}")
            print(excerpt(pt, ct, j))
            print(f"  elements before it: {i} identical ({sum(len(t) for _, t in ps[:i]):,} chars ≈ {sum(len(t) for _, t in ps[:i]) // 4:,} tok)")
            return
    if len(ps) != len(cs):
        print(f"  identical up to element {min(len(ps), len(cs))}; then {len(cs) - len(ps):+d} elements (normal turn growth)")
    else:
        print("  bodies identical")


def load_log():
    rows = []
    for line in open(LOG, encoding="utf-8"):
        try:
            rows.append(json.loads(line))
        except ValueError:
            pass
    return [r for r in rows if r.get("kind", r.get("tipo")) == "real" and r.get("n_msgs")]


def body_for(sha):
    hits = sorted(glob.glob(os.path.join(BODIES, "*-" + sha + ".json")))
    return json.load(open(hits[-1], encoding="utf-8")) if hits else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*", help="two body files to compare directly")
    ap.add_argument("--all", action="store_true", help="compare every consecutive pair, not only breaks")
    args = ap.parse_args()

    if len(args.files) == 2:
        compare(json.load(open(args.files[0], encoding="utf-8")), json.load(open(args.files[1], encoding="utf-8")))
        return

    rows = load_log()
    prev = None
    found = 0
    for r in rows:
        u = r.get("usage") or {}
        ctx = (u.get("input_tokens") or 0) + (u.get("cache_creation_input_tokens") or 0) + (u.get("cache_read_input_tokens") or 0)
        if prev:
            pu = prev.get("usage") or {}
            pctx = (pu.get("input_tokens") or 0) + (pu.get("cache_creation_input_tokens") or 0) + (pu.get("cache_read_input_tokens") or 0)
            cw = u.get("cache_creation_input_tokens") or 0
            is_break = cw > 0.2 * pctx and cw > 20000
            if is_break or args.all:
                found += 1
                print(f"{r['ts']}  {'BREAK' if is_break else 'pair '}  prev ctx {pctx:,} -> cw {cw:,} cr {u.get('cache_read_input_tokens'):,}  "
                      f"model {r.get('model')}  bodies {prev.get('body_sha')} -> {r.get('body_sha')}")
                pb, cb = body_for(prev.get("body_sha")), body_for(r.get("body_sha"))
                if pb and cb:
                    compare(pb, cb)
                else:
                    print("  body missing (set CACHE_PROXY_KEEP_BODIES and run the session through the proxy)")
        if ctx:
            prev = r
    if not found:
        print("no break in", LOG, "-", len(rows), "real calls")


if __name__ == "__main__":
    main()
