#!/usr/bin/env python3
"""The savings ledger: what each lever could have saved on YOUR transcripts.

Reads every Claude Code transcript under ~/.claude/projects, deduplicates the
API calls, and prices each avoidable event at API list prices. Every line it
prints is an arithmetic fact about the logs, not a forecast: "this many tokens
were written after an idle gap over 60 min; at 2x input price that is $X".
Whether you would actually recover $X depends on what you do instead (see
SAVINGS.md for the honest reading of each line).

    python tools/ledger.py                    # all sessions, list price by model
    python tools/ledger.py --last 100         # the 100 most recent transcripts
    python tools/ledger.py --price-input 5 --cap 200000 --ping-every 20 --max-pings 9
    python tools/ledger.py --json             # machine-readable
    python tools/ledger.py --until 2026-09-15 --no-subagents --price-input 5   # the SAVINGS.md base

Subagent transcripts (<session>/subagents/**/agent-*.jsonl) are counted by
default as side calls of their parent session; the total is printed split into
main thread and subagents. --no-subagents reads the parent transcripts only.

Prices: each call at the list price of its own message.model (MODEL_PRICES in
_common.py: input, 5m write, 1h write, cache read, output). Reads are 0.1x
input on Opus 5, 0.05x on Opus/Sonnet 5.5, 0.025x on Fable 5.1, so the levers
below the total are priced per call too. Writes with no TTL breakdown are
priced as 1h. --price-input P sets one flat sheet for every call (input P,
read 0.1 P, 1h write 2 P, 5m write 1.25 P, output 5 P): the Opus 5 multipliers
confirmed by regression on Claude Code's own `total_cost_usd`
(experiments/ab-config-vs-bare, residual 0), and the SAVINGS.md base.

Dedup: one assistant line per content block, same (message.id, requestId).
The call keeps the largest output_tokens of its lines (the first line is
written mid-stream) and counts as a tool turn if any line holds a tool_use.

If you are on a subscription, the dollars are quota-equivalent, not cash.
"""
import argparse
import json
import os
import statistics
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sessions import subagent_files, transcripts  # noqa: E402
from _common import PROJECTS, prices, sheet, ts  # noqa: E402,F401  (before_after imports prices from here)

SKIP = {"assistant", "user", "queue-operation", "last-prompt"}
# events that change the request prefix by construction (tools, system prompt, params); shared with rewrites.py
PREFIX_EVENTS = {
    "attachment:deferred_tools_delta", "attachment:mcp_instructions_delta", "attachment:skill_listing",
    "attachment:ultra_effort_enter", "system:model_refusal_fallback", "system:api_error",
    "attachment:dynamic_skill", "attachment:nested_memory", "attachment:directory", "attachment:file",
    "attachment:goal_status", "attachment:remote_session_change", "attachment:auto_mode",
    "permission-mode", "attachment:date_change",
}

LEVERS = ("ttl", "ttl-keepalive-net (blind pinger)", "ttl-keepalive-net (only when back in time)", "resume-or-model-switch",
          "effort-change", "other-prefix-change (tools/MCP/skills)", "hook-context-on-user-turn (correlation)",
          "unexplained (old client versions)", "history-cap", "skillOverrides", "terse-output -8%")


def per_m_input(model):
    return sheet(model)["input"] * 1e6


def call_price(c):
    """The list-price sheet of one call: its own model, and its own prompt size (Haiku 5.5 long context)."""
    return sheet(c["model"], c["input"] + c["cw"] + c["cr"])


def call_usd(c, price):
    """One call at one price sheet; the 5m part of the write at 1.25 P, the rest (1h or unlabelled) at 2 P."""
    return {"cache_read": c["cr"] * price["cr"],
            "cache_creation": c["cw5m"] * price["cw5m"] + (c["cw"] - c["cw5m"]) * price["cw1h"],
            "output": c["out"] * price["out"], "input": c["input"] * price["input"]}


def load(path, seen, side=False):
    """One list of calls (dedup) with the transcript events that sit between them. side=True: a subagent file.
    seen: dict (message.id, requestId) -> call, shared across files so a resumed copy only adds what is new."""
    lines = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for raw in f:
            try:
                lines.append(json.loads(raw))
            except ValueError:
                pass
    calls = []
    pending = set()
    for d in lines:
        t = d.get("type")
        if t == "assistant":
            m = d.get("message") or {}
            u = m.get("usage")
            if not u:
                continue
            key = (m.get("id"), d.get("requestId"))
            tool_use = any(isinstance(b, dict) and b.get("type") == "tool_use" for b in (m.get("content") or []))
            if key in seen:
                # one line per content block; output_tokens grows as the response streams, tool_use is
                # rarely the first block (thinking is, in 57% of responses)
                c = seen[key]
                c["out"] = max(c["out"], u.get("output_tokens") or 0)
                c["tool_turn"] = c["tool_turn"] or tool_use
                continue
            cc = u.get("cache_creation") or {}
            seen[key] = {
                "ts": d.get("timestamp", ""), "model": m.get("model", ""), "version": d.get("version", ""),
                "side": side or bool(d.get("isSidechain")),
                "input": u.get("input_tokens") or 0, "cw": u.get("cache_creation_input_tokens") or 0,
                "cr": u.get("cache_read_input_tokens") or 0, "out": u.get("output_tokens") or 0,
                "cw5m": cc.get("ephemeral_5m_input_tokens") or 0, "cw1h": cc.get("ephemeral_1h_input_tokens") or 0,
                "events": pending, "tool_turn": tool_use,
            }
            calls.append(seen[key])
            pending = set()
        elif t not in SKIP:
            pending.add(t)
            if t == "system":
                pending.add("system:" + str(d.get("subtype")))
            if t == "attachment":
                pending.add("attachment:" + str((d.get("attachment") or {}).get("type")))
    return calls


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project")
    ap.add_argument("--last", type=int, default=0, help="most recent N transcripts (0 = all)")
    ap.add_argument("--min-calls", type=int, default=5)
    ap.add_argument("--price-input", type=float, default=None,
                    help="flat US$ per M input tokens for every call (default: by message.model)")
    ap.add_argument("--until", help="YYYY-MM-DD: drop calls stamped after this day (UTC)")
    ap.add_argument("--no-subagents", action="store_true", help="skip <session>/subagents/ transcripts")
    ap.add_argument("--cap", type=int, default=200000, help="context cap for the history-length ceiling")
    ap.add_argument("--ping-every", type=int, default=20, help="keep-alive ping interval, minutes")
    ap.add_argument("--max-pings", type=int, default=9, help="keep-alive gives up after this many pings")
    ap.add_argument("--skill-tokens", type=int, default=2752, help="prefix tokens removed by skillOverrides (measured)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    flat = prices(args.price_input) if args.price_input else None

    def pr(c):
        return flat or call_price(c)

    seen = {}
    tot = Counter()
    usd = Counter()
    usd_who = Counter()             # main / side
    usd_model = Counter()
    n_side_calls = 0
    buckets = Counter()
    n_sessions = 0
    ledger = defaultdict(Counter)   # lever -> {"events", "tokens", "usd"}
    ctx_main = []
    hook_turns = Counter()          # (hook present?, current version?) -> boundaries
    hook_broke = Counter()
    hook_tokens = Counter()
    ttl_gaps = Counter()
    ttl_gap_tokens = Counter()
    ttl_gap_usd = Counter()

    for path in transcripts(args.project, args.last):
        calls = load(path, seen)
        if not args.no_subagents:
            for f in subagent_files(path):
                calls += load(f, seen, side=True)
        if args.until:
            calls = [c for c in calls if c["ts"][:10] <= args.until]
        if len(calls) < args.min_calls:
            continue
        n_sessions += 1
        for c in calls:
            for k in ("input", "cw", "cr", "out"):
                tot[k] += c[k]
            cu = call_usd(c, pr(c))
            ledger["terse-output -8%"]["usd"] += 0.08 * c["out"] * pr(c)["out"]
            usd.update(cu)
            usd_who["side" if c["side"] else "main"] += sum(cu.values())
            usd_model[c["model"] or "?"] += sum(cu.values())
            n_side_calls += c["side"]
            buckets[("side" if c["side"] else "main", "5m")] += c["cw5m"]
            buckets[("side" if c["side"] else "main", "1h")] += c["cw1h"]
            if not c["side"]:
                ctx = c["input"] + c["cw"] + c["cr"]
                ctx_main.append(ctx)
                ledger["skillOverrides"]["usd"] += args.skill_tokens * pr(c)["cr"]
                if ctx > args.cap:
                    ledger["history-cap"]["events"] += 1
                    ledger["history-cap"]["tokens"] += ctx - args.cap
                    ledger["history-cap"]["usd"] += (ctx - args.cap) * pr(c)["cr"]
        main = [c for c in calls if not c["side"]]
        for j in range(1, len(main)):
            p, c = main[j - 1], main[j]
            if not p["ts"] or not c["ts"]:
                continue
            pctx = p["input"] + p["cw"] + p["cr"]
            cctx = c["input"] + c["cw"] + c["cr"]
            if pctx < 20000:
                continue
            gap = (ts(c["ts"]) - ts(p["ts"])).total_seconds() / 60
            broke = c["cw"] > 0.2 * pctx and c["cw"] > 20000
            # keep-alive counterfactual. A blind pinger fires every `ping_every` idle minutes on EVERY
            # gap (whether or not the cache would have broken), up to `max_pings`, each ping a cache
            # read of the previous context. It only earns something on a TTL break it reached.
            pings = min(int(gap // args.ping_every), args.max_pings)
            if pings:
                ledger["ttl-keepalive-net (blind pinger)"]["usd"] -= pings * pctx * pr(p)["cr"]
            if not broke:
                continue
            rewrite_usd = c["cw"] * pr(c)["cw1h"]
            if gap > 60:
                ledger["ttl"]["events"] += 1
                ledger["ttl"]["tokens"] += c["cw"]
                gb = "60-120 min" if gap <= 120 else "120-200 min" if gap <= 200 else "200-480 min" if gap <= 480 else "> 480 min"
                ttl_gaps[gb] += 1
                ttl_gap_tokens[gb] += c["cw"]
                ttl_gap_usd[gb] += rewrite_usd
                ledger["ttl"]["usd"] += rewrite_usd
                if gap // args.ping_every <= args.max_pings:
                    gross = rewrite_usd
                    ledger["ttl-keepalive-net (blind pinger)"]["events"] += 1
                    ledger["ttl-keepalive-net (blind pinger)"]["tokens"] += c["cw"]
                    ledger["ttl-keepalive-net (blind pinger)"]["usd"] += gross
                    ledger["ttl-keepalive-net (only when back in time)"]["events"] += 1
                    ledger["ttl-keepalive-net (only when back in time)"]["tokens"] += c["cw"]
                    ledger["ttl-keepalive-net (only when back in time)"]["usd"] += gross - pings * pctx * pr(p)["cr"]
                continue
            if "synthetic" in p["model"] or (p["model"] and c["model"] and p["model"] != c["model"]):
                ledger["resume-or-model-switch"]["events"] += 1
                ledger["resume-or-model-switch"]["tokens"] += c["cw"]
                ledger["resume-or-model-switch"]["usd"] += rewrite_usd
                continue
            if cctx < 0.7 * pctx:
                continue  # prune/compact: the history really shrank, nothing to avoid
            ev = c["events"]
            if "attachment:ultra_effort_enter" in ev:
                ledger["effort-change"]["events"] += 1
                ledger["effort-change"]["tokens"] += c["cw"]
                ledger["effort-change"]["usd"] += rewrite_usd
            elif ev & PREFIX_EVENTS:
                ledger["other-prefix-change (tools/MCP/skills)"]["events"] += 1
                ledger["other-prefix-change (tools/MCP/skills)"]["tokens"] += c["cw"]
                ledger["other-prefix-change (tools/MCP/skills)"]["usd"] += rewrite_usd
            elif "attachment:hook_additional_context" in ev and not p["tool_turn"]:
                ledger["hook-context-on-user-turn (correlation)"]["events"] += 1
                ledger["hook-context-on-user-turn (correlation)"]["tokens"] += c["cw"]
                ledger["hook-context-on-user-turn (correlation)"]["usd"] += rewrite_usd
            else:
                ledger["unexplained (old client versions)"]["events"] += 1
                ledger["unexplained (old client versions)"]["tokens"] += c["cw"]
                ledger["unexplained (old client versions)"]["usd"] += rewrite_usd
                ledger["unexplained (old client versions)"][c["version"]] += 1
        # hook correlation on user-turn boundaries, no known prefix event, no gap, same model
        for j in range(1, len(main)):
            p, c = main[j - 1], main[j]
            if p["tool_turn"] or not p["ts"] or not c["ts"]:
                continue
            pctx = p["input"] + p["cw"] + p["cr"]
            cctx = c["input"] + c["cw"] + c["cr"]
            if pctx < 20000 or (ts(c["ts"]) - ts(p["ts"])).total_seconds() > 3600 or p["model"] != c["model"] or cctx < 0.7 * pctx:
                continue
            if c["events"] & PREFIX_EVENTS:
                continue
            key = ("hook" if "attachment:hook_additional_context" in c["events"] else "nohook",
                   "cur" if c["version"] >= "2.1.237" else "old")
            hook_turns[key] += 1
            if c["cw"] > 0.2 * pctx and c["cw"] > 20000 and c["cr"] <= 60000:
                hook_broke[key] += 1
                hook_tokens[key] += c["cw"]

    n_main_calls = len(ctx_main)
    ledger["skillOverrides"]["events"] = n_main_calls
    ledger["skillOverrides"]["tokens"] = args.skill_tokens * n_main_calls
    ledger["terse-output -8%"]["tokens"] = int(0.08 * tot["out"])

    for k in LEVERS:
        ledger[k]   # every lever in the JSON, even with no events
    usd = {k: usd[k] for k in ("cache_read", "cache_creation", "output", "input")}
    total = sum(usd.values())

    if args.json:
        print(json.dumps({"sessions": n_sessions, "calls_main": n_main_calls, "calls_side": n_side_calls,
                          "tokens": dict(tot), "usd": usd, "total_usd": total,
                          "usd_main": usd_who["main"], "usd_side": usd_who["side"], "usd_by_model": dict(usd_model), "buckets": {f"{a}:{b}": v for (a, b), v in buckets.items()},
                          "ledger": {k: dict(v) for k, v in ledger.items()},
                          "ttl_gaps": {k: [ttl_gaps[k], ttl_gap_tokens[k]] for k in ttl_gaps},
                          "hook": {f"{a}:{b}": [hook_turns[(a, b)], hook_broke[(a, b)], hook_tokens[(a, b)]]
                                   for (a, b) in hook_turns}}, indent=1))
        return

    if not ctx_main:
        sys.exit("no transcripts with >= %d calls under %s" % (args.min_calls, PROJECTS))
    print(f"sessions {n_sessions:,}  main-thread calls {n_main_calls:,}  subagent calls {n_side_calls:,}  "
          f"(min {args.min_calls} calls/session{', until ' + args.until if args.until else ''})")
    print(f"context per main-thread call: mean {statistics.mean(ctx_main):,.0f}  median {statistics.median(ctx_main):,.0f}  "
          f"p90 {sorted(ctx_main)[int(0.9 * len(ctx_main))]:,}")
    sheet = f"P={args.price_input}/M" if args.price_input else "P by model"
    print(f"\nAPI-equivalent total at {sheet}: ${total:,.2f}")
    for k, v in usd.items():
        print(f"  {k:15} ${v:10,.2f}  {100 * v / total:4.0f}%")
    for who, label in (("main", "main thread"), ("side", "subagents")):
        print(f"  {label:15} ${usd_who[who]:10,.2f}  {100 * usd_who[who] / total:4.0f}%")
    print("by model:")
    for m, v in usd_model.most_common():
        print(f"  {m:28} ${v:10,.2f}  {100 * v / total:4.0f}%")
    print("\ncache writes by TTL bucket (tokens):")
    for (who, b), v in sorted(buckets.items()):
        print(f"  {who:5} {b:3} {v:15,}")
    print("\nledger — what each lever touches on these logs (API-equivalent, ceiling unless marked net):")
    print(f"  {'lever':46} {'events':>8} {'tokens':>16} {'US$':>11} {'% of total':>10}")
    for k in LEVERS:
        v = ledger[k]
        print(f"  {k:46} {v['events']:8,} {v['tokens']:16,} {v['usd']:11,.2f} {100 * v['usd'] / total:9.2f}%")
    print(f"\n  ttl: rewrites after an idle gap > 60 min, priced at 2x (1h write). Avoidable by keep-alive or by")
    print(f"       handoff + /clear before leaving; the 'net' line subtracts {args.ping_every}-min pings (a cache read")
    print(f"       of the previous context each) and charges {args.max_pings} wasted pings when the gap outlived the pinger.")
    print(f"  history-cap: cache_read above {args.cap:,} per call, at read price. Arithmetic ceiling of 'never let a")
    print(f"       session grow past the cap'; NOT a forecast — the work would need more sessions and re-reads.")
    print(f"  skillOverrides: {args.skill_tokens:,} prefix tokens x every main call at 0.1x (measured delta).")
    print(f"  terse-output: 8% of output tokens (measured on Haiku pt-BR, n=20, sd 25%).")
    print("\nttl re-writes by idle gap (how long the session sat before it came back):")
    for gb in ("60-120 min", "120-200 min", "200-480 min", "> 480 min"):
        print(f"  {gb:12} events {ttl_gaps[gb]:5,}  tokens {ttl_gap_tokens[gb]:13,}  ${ttl_gap_usd[gb]:9,.2f}")
    print("\nhook additionalContext on user-turn boundaries (no other prefix event, same model, gap <= 60 min):")
    for key in sorted(hook_turns):
        n, b, t = hook_turns[key], hook_broke[key], hook_tokens[key]
        print(f"  {key[0]:6} {key[1]:3}  boundaries {n:7,}  full re-writes {b:5,}  {100 * b / n:5.2f}%  tokens {t:13,}")
    unexpl = ledger["unexplained (old client versions)"]
    # everything else in this Counter is a per-version count; matching "2." would hide a 3.x client
    vers = sorted(((k, v) for k, v in unexpl.items() if k not in ("events", "tokens", "usd")), key=lambda x: -x[1])[:5]
    print(f"\nunexplained re-writes by version (top 5): {vers}")


if __name__ == "__main__":
    main()
