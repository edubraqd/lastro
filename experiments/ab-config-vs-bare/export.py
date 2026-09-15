#!/usr/bin/env python3
"""Strip the answer text from results.jsonl before sharing it.

    python export.py results.jsonl data/results-YYYY-MM-DD.jsonl

The `result` field holds the model's final answer, which quotes your project
(file paths, names, data rows). Everything else — arm, task id, session id,
wall time, Claude Code's cost, usage from the API and from the transcript,
answer length, oracle verdict — is what the analysis needs and carries nothing
from the project. analyze.py works on the exported file; judge.py and
decomp.py need the original (answer text / transcripts on disk).
"""
import json
import sys

src, dst = sys.argv[1], sys.argv[2]
n = 0
with open(dst, "w", encoding="utf-8") as out:
    for line in open(src, encoding="utf-8"):
        e = json.loads(line)
        e.pop("result", None)
        if not e.get("err"):
            e.pop("err", None)
        out.write(json.dumps(e, ensure_ascii=False) + "\n")
        n += 1
print(f"{n} runs -> {dst} (no answer text)")
