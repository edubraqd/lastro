#!/usr/bin/env python3
"""Start N copies of hooks/handoff-load.js in the same instant against a sandbox
and count how many of them received each handoff. One is right; more is the
race this test found on 20/09 (2-6 of 28 before the lock in 7402af4).

    python tools/race_test.py                      # 28 starts, 1 file, 3 rounds
    python tools/race_test.py --n 28 --files 8 --rounds 5
    python tools/race_test.py --json

Sandbox: CLAUDE_CONFIG_DIR/race_home (its own peaks file) and CLAUDE_CONFIG_DIR/
race_proj/.claude (the handoff files), both created and removed here. Touches
nothing under ~/.claude unless CLAUDE_CONFIG_DIR points there — it defaults to a
temp dir. Needs node on PATH.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import utf8_stdout  # noqa: E402

HOOK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hooks", "handoff-load.js")


def one_round(base, n, files):
    home = os.path.join(base, "race_home")
    proj = os.path.join(base, "race_proj")
    dot = os.path.join(proj, ".claude")
    shutil.rmtree(home, ignore_errors=True)
    shutil.rmtree(proj, ignore_errors=True)
    os.makedirs(home)
    os.makedirs(dot)
    owners = ["%08x" % (0xa0000000 + i) + "0" * 8 for i in range(files)]
    peaks = {o: {"peak": 1, "turns_above": 0, "project": proj} for o in owners}
    with open(os.path.join(home, ".context-peaks.json"), "w", encoding="utf-8") as fh:
        json.dump(peaks, fh)
    now = time.time()
    for i, o in enumerate(owners):
        p = os.path.join(dot, "handoff-%s.md" % o[:8])
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("# race file %d\n" % i)
        os.utime(p, (now - 60 * (i + 1), now - 60 * (i + 1)))   # distinct ages, newest first
    env = dict(os.environ, CLAUDE_CONFIG_DIR=home, CANARY="0", CLAUDE_PROJECT_DIR=proj)
    env.pop("HANDOFF_HOURS", None)
    procs = [subprocess.Popen(["node", HOOK], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env) for _ in range(n)]
    for i, p in enumerate(procs):   # feed every stdin before waiting on any, so the hooks overlap
        p.stdin.write(json.dumps({"source": "startup", "cwd": proj, "session_id": "%016x" % (0xb0000000 + i)}).encode("utf-8"))
        p.stdin.close()
        p.stdin = None   # communicate() would flush the closed pipe: ValueError on POSIX before 3.13
    outs = [p.communicate()[0].decode("utf-8", "replace") for p in procs]
    delivered = {}
    for i in range(files):
        delivered["handoff-%s.md" % owners[i][:8]] = sum(1 for o in outs if "# race file %d" % i in o)
    with open(os.path.join(home, ".context-peaks.json"), encoding="utf-8") as fh:
        pk = json.load(fh)
    marked = sum(1 for o in owners if pk.get(o, {}).get("handoff_loaded_by"))
    got_none = sum(1 for o in outs if "# race file" not in o)
    shutil.rmtree(home, ignore_errors=True)
    shutil.rmtree(proj, ignore_errors=True)
    return {"delivered": delivered, "delivered_max": max(delivered.values()), "marked": marked, "got_none": got_none}


def main():
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--n", type=int, default=28, help="parallel starts")
    ap.add_argument("--files", type=int, default=1, help="handoff files waiting in the project")
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    given = os.environ.get("CLAUDE_CONFIG_DIR")
    base = given or tempfile.mkdtemp(prefix="ccf-race-")
    os.makedirs(base, exist_ok=True)
    try:
        rounds = [one_round(base, a.n, a.files) for _ in range(a.rounds)]
    finally:
        if not given:   # ours: remove it; a dir the caller named is theirs (one_round already empties its sandbox)
            shutil.rmtree(base, ignore_errors=True)
    worst = max(r["delivered_max"] for r in rounds)
    if a.json:
        print(json.dumps({"n": a.n, "files": a.files, "rounds": rounds, "worst": worst}, indent=1))
    else:
        for i, r in enumerate(rounds):
            print("round %d: %s  marked %d/%d  got nothing %d/%d" % (i + 1, ", ".join("%s x%d" % kv for kv in r["delivered"].items()), r["marked"], a.files, r["got_none"], a.n))
        print("worst: one file delivered to %d of %d parallel starts (%s)" % (worst, a.n, "ok" if worst <= 1 else "RACE"))
    sys.exit(0 if worst <= 1 else 2)


if __name__ == "__main__":
    main()
