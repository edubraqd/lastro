#!/usr/bin/env python3
"""Before/after: did a change on day X move the bill on YOUR transcripts?

Splits sessions by the date of their first API call and prints, per period
and per day, the numbers the levers in SAVINGS.md are supposed to move:
cost per call, context per main-thread call (median, p90, share above the
cap), TTL re-writes, first-call prefix write, output per call, compactions.
Same dedup and prices as ledger.py; every column is arithmetic on the logs.

    python tools/before_after.py --split 2026-09-14                 # 14 days before vs after
    python tools/before_after.py --split 2026-09-14 --days 7        # 7 days each side
    python tools/before_after.py --split 2026-09-14 --daily         # one row per day too
    python tools/before_after.py --split 2026-09-14 --json

Read report/usage-real-2026-09-17.md before quoting a difference as a
saving: the periods are different work, not an A/B. What makes the number
credible is a step on the split day with calls/day roughly unchanged.
"""
import argparse
import datetime as dt
import json
import os
import statistics
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ledger import load  # noqa: E402
from sessions import transcripts  # noqa: E402
from _common import ts  # noqa: E402


def new_bucket():
    return {"sessions": 0, "calls": 0, "usd": 0.0, "cr": 0, "cw": 0, "out": 0, "ctx": [], "over": 0,
            "ttl": 0, "ttl_tok": 0, "first_cw": [], "days": set(), "peak": [], "compact": 0, "sess_calls": []}


def p90(xs):
    return sorted(xs)[int(len(xs) * 0.9)] if xs else 0


def add_session(b, calls, price, cap):
    b["sessions"] += 1
    b["days"].add(calls[0]["ts"][:10])
    b["sess_calls"].append(len(calls))
    main = [c for c in calls if not c["side"]]
    if main:
        b["first_cw"].append(main[0]["cw"])
    peak = 0
    for c in calls:
        b["calls"] += 1
        b["usd"] += c["input"] * price["input"] + c["cr"] * price["cr"] + c["cw"] * price["cw"] + c["out"] * price["out"]
        b["cr"] += c["cr"]
        b["cw"] += c["cw"]
        b["out"] += c["out"]
        if not c["side"]:
            ctx = c["input"] + c["cw"] + c["cr"]
            b["ctx"].append(ctx)
            peak = max(peak, ctx)
            if ctx > cap:
                b["over"] += 1
    b["peak"].append(peak)
    for j in range(1, len(main)):
        p, c = main[j - 1], main[j]
        if not p["ts"] or not c["ts"]:
            continue
        pctx = p["input"] + p["cw"] + p["cr"]
        cctx = c["input"] + c["cw"] + c["cr"]
        if pctx < 20000:
            continue
        gap = (ts(c["ts"]) - ts(p["ts"])).total_seconds() / 60
        if c["cw"] > 0.2 * pctx and c["cw"] > 20000 and gap > 60:   # same definition as ledger.py / ttl.py
            b["ttl"] += 1
            b["ttl_tok"] += c["cw"]
        if cctx < 0.7 * pctx and pctx > 100000:                      # history shrank: compact or prune
            b["compact"] += 1


def row(b, price, cap):
    days = max(len(b["days"]), 1)
    return {
        "days": len(b["days"]), "sessions": b["sessions"], "calls": b["calls"],
        "usd": round(b["usd"], 2), "usd_per_day": round(b["usd"] / days, 2),
        "usd_per_call": round(b["usd"] / b["calls"], 4) if b["calls"] else 0,
        "ctx_median": int(statistics.median(b["ctx"])) if b["ctx"] else 0,
        "ctx_p90": int(p90(b["ctx"])),
        "over_cap_pct": round(100 * b["over"] / len(b["ctx"]), 1) if b["ctx"] else 0,
        "peak_median": int(statistics.median(b["peak"])) if b["peak"] else 0,
        "ttl_events": b["ttl"], "ttl_usd": round(b["ttl_tok"] * price["cw"], 2),
        "first_cw_median": int(statistics.median(b["first_cw"])) if b["first_cw"] else 0,
        "out_per_call": round(b["out"] / b["calls"], 1) if b["calls"] else 0,
        "compact": b["compact"],
        "calls_per_session_median": int(statistics.median(b["sess_calls"])) if b["sess_calls"] else 0,
        "share": {
            "cache_read": round(100 * b["cr"] * price["cr"] / b["usd"], 1) if b["usd"] else 0,
            "cache_write": round(100 * b["cw"] * price["cw"] / b["usd"], 1) if b["usd"] else 0,
            "output": round(100 * b["out"] * price["out"] / b["usd"], 1) if b["usd"] else 0,
        },
    }


def k(n):
    return "%dk" % round(n / 1000)


HDR = ("{:<14}{:>5}{:>5}{:>7}{:>8}{:>8}{:>9}{:>8}{:>8}{:>6}{:>9}{:>5}{:>7}{:>8}{:>9}{:>8}"
       .format("period", "days", "sess", "calls", "US$", "US$/day", "US$/call", "ctx med", "ctx p90", ">cap",
               "peak med", "TTL", "TTL$", "1st cw", "out/call", "compact"))


def fmt(name, r):
    return ("{:<14}{:>5}{:>5}{:>7}{:>8.0f}{:>8.1f}{:>9.3f}{:>8}{:>8}{:>5.0f}%{:>9}{:>5}{:>7.0f}{:>8}{:>9.0f}{:>8}"
            .format(name, r["days"], r["sessions"], r["calls"], r["usd"], r["usd_per_day"], r["usd_per_call"],
                    k(r["ctx_median"]), k(r["ctx_p90"]), r["over_cap_pct"], k(r["peak_median"]), r["ttl_events"],
                    r["ttl_usd"], k(r["first_cw_median"]), r["out_per_call"], r["compact"]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--split", required=True, help="first day of the 'after' period, YYYY-MM-DD")
    ap.add_argument("--days", type=int, default=14, help="days on each side of the split (0 = everything)")
    ap.add_argument("--project")
    ap.add_argument("--min-calls", type=int, default=5)
    ap.add_argument("--cap", type=int, default=200000)
    ap.add_argument("--price-input", type=float, default=5.0, help="US$ per M input tokens (Opus-class: 5)")
    ap.add_argument("--daily", action="store_true", help="also one row per day")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    split = dt.date.fromisoformat(args.split)
    lo = (split - dt.timedelta(days=args.days)).isoformat() if args.days else "0000"
    hi = (split + dt.timedelta(days=args.days)).isoformat() if args.days else "9999"
    P = args.price_input / 1e6
    price = {"input": P, "cr": 0.1 * P, "cw": 2.0 * P, "out": 5.0 * P}

    seen = set()
    periods = {"before": new_bucket(), "after": new_bucket()}
    daily = defaultdict(new_bucket)
    for path in transcripts(args.project, 0):
        calls = load(path, seen)
        if len(calls) < args.min_calls:
            continue
        day = calls[0]["ts"][:10]
        if not (lo <= day < hi):
            continue
        add_session(periods["after" if day >= args.split else "before"], calls, price, args.cap)
        if args.daily:
            add_session(daily[day], calls, price, args.cap)

    out = {"split": args.split, "window_days": args.days, "cap": args.cap,
           "before": row(periods["before"], price, args.cap), "after": row(periods["after"], price, args.cap)}
    if args.daily:
        out["daily"] = {d: row(daily[d], price, args.cap) for d in sorted(daily)}
    b, a = out["before"], out["after"]
    if b["calls"] and a["calls"]:
        out["delta"] = {key: round(100 * (a[key] - b[key]) / b[key], 1) if b[key] else None
                        for key in ("usd_per_day", "usd_per_call", "ctx_median", "ctx_p90", "out_per_call", "first_cw_median")}

    if args.json:
        print(json.dumps(out, indent=1))
        return
    if not (b["calls"] or a["calls"]):
        sys.exit("no sessions with >= %d calls between %s and %s" % (args.min_calls, lo, hi))
    print(HDR)
    print(fmt("before", b))
    print(fmt("after", a))
    if "delta" in out:
        d = out["delta"]
        print("\ndelta after vs before: US$/day %+.0f%%, US$/call %+.0f%%, ctx median %+.0f%%, ctx p90 %+.0f%%, "
              "out/call %+.0f%%, first cache write %+.0f%%" % tuple(d[key] or 0 for key in
              ("usd_per_day", "usd_per_call", "ctx_median", "ctx_p90", "out_per_call", "first_cw_median")))
    for name in ("before", "after"):
        r = out[name]
        print("%s: cache read %.0f%%  write %.0f%%  output %.0f%%   calls/session median %d"
              % (name, r["share"]["cache_read"], r["share"]["cache_write"], r["share"]["output"], r["calls_per_session_median"]))
    if args.daily:
        print()
        print(HDR.replace("period        ", "day           "))
        for d, r in out["daily"].items():
            print(fmt(d, r))
    print("\nA step on the split day with calls/day unchanged is evidence; a drift is not. See report/usage-real-2026-09-17.md.")


if __name__ == "__main__":
    main()
