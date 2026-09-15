#!/usr/bin/env python3
"""Blind judge for tasks without a deterministic oracle.

    python judge.py [results.jsonl]

Haiku, isolated (`--setting-sources "" --tools "" --strict-mcp-config
--max-turns 1`), sees ONLY the answer text and the rubric — never the arm, the
task prompt, or the project. Writes judged.jsonl with YES/NO per run. Also
useful as a cross-check on regex oracles: give those tasks a rubric too and
compare (2026-09-14: 12/12 agreement on the two tasks checked).
"""
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "results.jsonl")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(os.path.abspath(path)))  # tasks.py next to results.jsonl wins
import tasks  # noqa: E402

CLAUDE = os.environ.get("CLAUDE_BIN") or shutil.which("claude") or "claude"
RUBRICS = {t: d["judge"] for t, d in tasks.TASKS.items() if d.get("judge")}


def judge(rubric, txt):
    p = (f"You are an evaluator. Criterion: {rubric}\n\nANSWER UNDER EVALUATION:\n<<<\n{txt}\n>>>\n\n"
         f"Reply with exactly one word: YES or NO.")
    env = dict(os.environ, PYTHONIOENCODING="utf-8", CANARY="0", CANARIO="0", CLAUDE_CODE_DISABLE_AUTO_MEMORY="1")
    # prompt via stdin: on Windows `claude` resolves to claude.cmd and cmd.exe
    # would treat the <<< >>> delimiters in an argv prompt as redirections
    r = subprocess.run([CLAUDE, "-p", "--model", "haiku", "--setting-sources", "", "--strict-mcp-config",
                        "--max-turns", "1", "--tools", ""], input=p,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, cwd=HERE, timeout=300)
    return r.stdout.strip().upper()


out = path.replace("results", "judged")
done = set()
if os.path.exists(out):
    for l in open(out, encoding="utf-8"):
        e = json.loads(l)
        done.add((e["task"], e["arm"], e["rep"]))
for l in open(path, encoding="utf-8"):
    e = json.loads(l)
    if e["task"] not in RUBRICS or (e["task"], e["arm"], e["rep"]) in done:
        continue
    if not e.get("result"):
        sys.exit("results.jsonl has no `result` text (exported copy?) — the judge needs the original file")
    v = judge(RUBRICS[e["task"]], e["result"])
    rec = dict(task=e["task"], arm=e["arm"], rep=e["rep"], judge=v, oracle=e["ok"])
    open(out, "a", encoding="utf-8").write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(rec, flush=True)
