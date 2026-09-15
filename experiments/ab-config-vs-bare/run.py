#!/usr/bin/env python3
"""A/B: Claude Code with your configuration vs. bare, on your own tasks, in `claude -p`.

    python run.py --project /path/to/repo [--reps 3] [--workers 3] [--only t1_fact] [--dry]

Arms (each run is a fresh session in the project directory):
  bare    --setting-sources ""  + CLAUDE_CODE_DISABLE_AUTO_MEMORY=1
          (probed 2026-09-14: without the env var the auto-memory still loads)
  config  --setting-sources user,project,local  (everything as you have it)
  nore    config + CLAUDE_CODE_TOTAL_TOKENS_REMINDER=off  (no <total_tokens> block;
          the env var outranks settings.json, probed in the 2.1.272 binary)

--arms a,b picks the pair (default bare,config); --out picks the results file.

Both arms: --strict-mcp-config (no MCP in either), --dangerously-skip-permissions,
--max-turns 40, CANARY=0 (a context canary only makes sense across sessions).

Per run it records: wall time, Claude Code's own `total_cost_usd` and `usage`
(from --output-format json), and the deduplicated usage read from the session
transcript (~/.claude/projects/<encoded cwd>/<session>.jsonl), plus the oracle
verdict from tasks.py. Output: results.jsonl (append-only; re-running skips
runs already done, so a crash is safe to resume).

Costs quota: 48 runs of 8 short tasks on Opus were ~US$12 API-equivalent.
"""
import json
import os
import random
import re
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tasks  # noqa: E402  (copy tasks.example.py to tasks.py and edit)

CLAUDE = os.environ.get("CLAUDE_BIN") or shutil.which("claude") or "claude"
MODEL = os.environ.get("AB_MODEL", "claude-opus-5")
RUNS = os.path.join(HERE, "runs")
OUT = os.path.join(HERE, "results.jsonl")
lock = threading.Lock()

ARMS = {
    "bare": dict(flags=["--setting-sources", ""], env={"CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1"}),
    "config": dict(flags=["--setting-sources", "user,project,local"], env={}),
    "nore": dict(flags=["--setting-sources", "user,project,local"],
                 env={"CLAUDE_CODE_TOTAL_TOKENS_REMINDER": "off"}),
}


def jsonl_dir(project):
    """Claude Code stores transcripts under ~/.claude/projects/<cwd with every non-alnum char -> '-'>."""
    enc = re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(project))
    return os.path.join(os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude"), "projects", enc)


def usage_jsonl(path):
    """Deduplicated usage for one session transcript (one line per content block, same usage on each)."""
    seen = set()
    tot = dict(calls=0, input=0, cw=0, cr=0, cw5m=0, cw1h=0, output=0, tool_uses=0, models={}, first_cw=None)
    if not os.path.exists(path):
        return tot
    for line in open(path, encoding="utf-8", errors="replace"):
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get("type") != "assistant":
            continue
        m = e.get("message") or {}
        for b in m.get("content") or []:
            if isinstance(b, dict) and b.get("type") == "tool_use":
                tot["tool_uses"] += 1
            if isinstance(b, dict) and b.get("type") == "text" and b.get("text"):
                tot["last_text"] = b["text"]
        u = m.get("usage")
        mid = m.get("id")
        if not u or not mid or mid in seen:
            continue
        seen.add(mid)
        tot["calls"] += 1
        tot["input"] += u.get("input_tokens", 0)
        tot["cw"] += u.get("cache_creation_input_tokens", 0)
        tot["cr"] += u.get("cache_read_input_tokens", 0)
        tot["output"] += u.get("output_tokens", 0)
        cc = u.get("cache_creation") or {}
        tot["cw5m"] += cc.get("ephemeral_5m_input_tokens", 0)
        tot["cw1h"] += cc.get("ephemeral_1h_input_tokens", 0)
        if tot["first_cw"] is None:
            tot["first_cw"] = u.get("cache_creation_input_tokens", 0)
        tot["models"][m.get("model", "?")] = tot["models"].get(m.get("model", "?"), 0) + 1
    return tot


def one(task, arm, rep, project, dry=False, out=OUT):
    tag = f"{task}_{arm}_r{rep}"
    rundir = os.path.join(RUNS, tag)
    fx = tasks.TASKS[task].get("fixture")
    prompt = tasks.TASKS[task]["prompt"].format(dir=rundir)
    cmd = [CLAUDE, "-p", prompt, "--model", MODEL, "--output-format", "json", "--strict-mcp-config",
           "--dangerously-skip-permissions", "--max-turns", "40"] + ARMS[arm]["flags"]
    env = dict(os.environ, PYTHONIOENCODING="utf-8", CANARY="0", CANARIO="0", **ARMS[arm]["env"])
    if dry:
        print(tag, cmd[:3], "...")
        return None
    if os.path.exists(rundir):
        shutil.rmtree(rundir)
    if fx:
        shutil.copytree(os.path.join(HERE, fx), rundir, ignore=shutil.ignore_patterns("__pycache__"))
    else:
        os.makedirs(rundir)
    t0 = time.time()
    try:
        r = subprocess.run(cmd, cwd=project, env=env, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=1200)
        wall = time.time() - t0
        try:
            d = json.loads(r.stdout)
        except ValueError:
            d = {"result": r.stdout[-2000:], "_stderr": r.stderr[-1000:], "_rc": r.returncode}
    except subprocess.TimeoutExpired:
        wall = time.time() - t0
        d = {"result": "", "_timeout": True}
    sid = d.get("session_id", "")
    time.sleep(2)  # the transcript is flushed slightly after the process exits
    u = usage_jsonl(os.path.join(jsonl_dir(project), sid + ".jsonl")) if sid else {}
    # read the final text from the transcript: on Windows the exe's stdout mangles non-ASCII
    txt = (u.get("last_text") if u else "") or d.get("result") or ""
    rec = dict(task=task, arm=arm, rep=rep, sid=sid, wall=round(wall, 1), turns=d.get("num_turns"),
               cost_usd=d.get("total_cost_usd"), api_usage=d.get("usage"),
               jsonl={k: v for k, v in u.items() if k != "last_text"}, chars=len(txt),
               ok=tasks.grade(task, txt, rundir), result=txt,
               err=d.get("_stderr") or d.get("_timeout") or d.get("is_error"))
    with lock:
        with open(out, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"{tag:26s} ok={rec['ok']} calls={u.get('calls')} cr={u.get('cr')} cw={u.get('cw')} "
              f"out={u.get('output')} wall={rec['wall']} err={rec['err']}", flush=True)
    return rec


def main():
    a = sys.argv[1:]
    if "--project" not in a:
        sys.exit("usage: run.py --project <dir> [--reps 3] [--workers 3] [--only t1,t2] [--dry]")
    project = os.path.abspath(a[a.index("--project") + 1])
    reps = int(a[a.index("--reps") + 1]) if "--reps" in a else 3
    workers = int(a[a.index("--workers") + 1]) if "--workers" in a else 3
    only = a[a.index("--only") + 1].split(",") if "--only" in a else None
    dry = "--dry" in a
    arms = a[a.index("--arms") + 1].split(",") if "--arms" in a else ["bare", "config"]
    out = os.path.abspath(a[a.index("--out") + 1]) if "--out" in a else OUT
    for arm in arms:
        if arm not in ARMS:
            sys.exit(f"unknown arm {arm!r}; have {list(ARMS)}")
    os.makedirs(RUNS, exist_ok=True)
    done = set()
    if os.path.exists(out) and not dry:
        for line in open(out, encoding="utf-8"):
            e = json.loads(line)
            if e.get("sid") and not e.get("err"):
                done.add((e["task"], e["arm"], e["rep"]))
    rnd = random.Random(42)
    order = list(tasks.TASKS)
    rnd.shuffle(order)
    if only:
        order = [t for t in order if t in only]
    plan = []
    for t in order:
        for rep in range(1, reps + 1):
            for arm in (arms if rep % 2 else arms[::-1]):  # ABBA
                if (t, arm, rep) not in done:
                    plan.append((t, arm, rep))
    for t in {p[0] for p in plan}:
        fx = tasks.TASKS[t].get("fixture")
        if fx and not os.path.isdir(os.path.join(HERE, fx)):
            sys.exit(f"{t}: fixture directory {fx!r} not found next to run.py")
    print(f"{len(plan)} runs, {workers} workers, already done {len(done)}, arms {arms}, out {out}", flush=True)
    with ThreadPoolExecutor(workers) as ex:
        list(ex.map(lambda p: one(*p, project=project, dry=dry, out=out), plan))


if __name__ == "__main__":
    main()
