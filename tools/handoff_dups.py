#!/usr/bin/env python3
"""How many times was the same handoff injected, and what did the extras cost?

    python tools/handoff_dups.py                 # every transcript under CLAUDE_CONFIG_DIR/projects
    python tools/handoff_dups.py --project motor # project dir name filter
    python tools/handoff_dups.py --json
    python tools/handoff_dups.py --since 2026-09-20   # count loads from that day on

An injection is a SessionStart `hook_additional_context` item that starts with
the handoff-load phrase (en or pt). A file loaded into two or more sessions is a
duplicate: before 7402af4 the loader had no lock, and before 07c0106 no mark at
all, so parallel `claude -p` runs and successive sessions in one project all
took the newest file (measured: one file into 28 sessions, 124 extras in a week).
A line that resume/fork copied into another transcript (same line uuid, same
text) is one load, not two; the same file name with a different body is a
rewrite, a new handoff, not a duplicate. The body is hashed from `<handoff` on:
the header carries the file's age, which differs on every load.

Cost of an extra: its characters / 3.5 as tokens, re-read on every API call of
that session (cache read), written once (cache write). Aggregates only: no
transcript text, no file bodies.
"""
import argparse
import collections
import glob
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import PROJECTS, utf8_stdout  # noqa: E402
from sessions import iter_calls  # noqa: E402

PHRASE = re.compile(r'^(?:HANDOFF DA SESSAO ANTERIOR|HANDOFF FROM THE PREVIOUS SESSION) \((handoff-[0-9a-f]{8}\.md),')


def injections(path):
    """(file name, chars, line uuid, body hash, timestamp) for each handoff injection in one transcript."""
    out = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if "hook_additional_context" not in line:
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue
            a = d.get("attachment") or {}
            if a.get("type") != "hook_additional_context":
                continue
            for item in a.get("content") or []:
                m = PHRASE.match(item)
                if m:
                    body = item[item.find("<handoff"):] if "<handoff" in item else item
                    out.append((m.group(1), len(item), d.get("uuid"),
                                hashlib.sha1(body.encode("utf-8")).hexdigest(), d.get("timestamp") or ""))
    return out


def scan(project_filter, read_per_m, write_per_m, since=None):
    paths = glob.glob(os.path.join(PROJECTS, "*", "*.jsonl"))
    if project_filter:
        paths = [p for p in paths if project_filter.lower() in os.path.basename(os.path.dirname(p)).lower()]
    per_ver = collections.defaultdict(list)   # (file, body hash) -> [(ts, session, chars, calls)]
    seen = set()                               # (line uuid, body hash) already counted
    for p in sorted(paths, key=os.path.getmtime):
        inj = []
        for name, chars, uuid, digest, ts in injections(p):
            if uuid and (uuid, digest) in seen:
                continue                       # copied by resume/fork: the same load
            seen.add((uuid, digest))
            inj.append((name, chars, digest, ts))
        if not inj:
            continue
        calls = sum(1 for _ in iter_calls(p, seen=set()))
        sid = os.path.basename(p)[:-6]
        for name, chars, digest, ts in inj:
            per_ver[(name, digest)].append((ts, sid, chars, calls))
    # The first load in time is the legitimate one, even before --since; the window
    # only picks which loads (and extras) are counted.
    win = lambda ts: not since or ts[:10] >= since   # noqa: E731
    for v in per_ver.values():
        v.sort(key=lambda e: e[0])
    n = sum(1 for v in per_ver.values() for e in v if win(e[0]))
    files = {k[0] for k, v in per_ver.items() if any(win(e[0]) for e in v)}
    dups = {k: [e for e in v[1:] if win(e[0])] for k, v in per_ver.items()}
    dups = {k: x for k, x in dups.items() if x}
    reread = write = 0.0
    for x in dups.values():
        for _ts, _sid, chars, calls in x:
            reread += chars / 3.5 * calls
            write += chars / 3.5
    top = sorted(dups.items(), key=lambda kv: -len(kv[1]))
    return {
        "transcripts": len(paths), "injections": n, "files": len(files),
        "files_in_2_or_more": len(dups), "extra_injections": sum(len(x) for x in dups.values()),
        "extra_reread_tokens": round(reread), "extra_write_tokens": round(write),
        "extra_usd": round(reread / 1e6 * read_per_m + write / 1e6 * write_per_m, 4),
        "top": [{"file": k[0], "sessions": len(x) + 1, "chars": per_ver[k][0][2], "calls_in_extras": sum(e[3] for e in x)}
                for k, x in top[:15]],
    }


def day(s):
    """argparse type for --since: AAAA-MM-DD."""
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        raise argparse.ArgumentTypeError("expected AAAA-MM-DD, got %r" % s)
    return s


def main():
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--project", help="substring of the project dir name under CLAUDE_CONFIG_DIR/projects")
    ap.add_argument("--price-read", type=float, default=0.5, help="US$ per M cache-read tokens (Opus: 0.5)")
    ap.add_argument("--price-write", type=float, default=10.0, help="US$ per M cache-write tokens (Opus 1h: 10)")
    ap.add_argument("--since", type=day, help="AAAA-MM-DD: count only loads from that day on (UTC)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    r = scan(a.project, a.price_read, a.price_write, a.since)
    if not r["injections"]:
        sys.stderr.write("no handoff injection found under %s (%d transcripts)\n" % (PROJECTS, r["transcripts"]))
        sys.exit(1)
    if a.json:
        print(json.dumps(r, indent=1))
        return
    print("%d injections of %d handoff files in %d transcripts; %d files loaded into 2+ sessions, %d extra injections"
          % (r["injections"], r["files"], r["transcripts"], r["files_in_2_or_more"], r["extra_injections"]))
    print("extras: ~%.2fM tokens re-read + %dk written = ~US$%.2f at %.2f/%.2f per M"
          % (r["extra_reread_tokens"] / 1e6, r["extra_write_tokens"] / 1e3, r["extra_usd"], a.price_read, a.price_write))
    for t in r["top"]:
        print("  %-22s x%-3d %5d chars  %5d calls in the extras" % (t["file"], t["sessions"], t["chars"], t["calls_in_extras"]))


if __name__ == "__main__":
    main()
