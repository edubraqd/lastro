# Exported runs

`results-<date>.jsonl`: one line per run, produced by `../export.py` from the
harness output — arm, task id, repetition, session id, wall time, Claude
Code's `total_cost_usd` and `usage`, the deduplicated transcript usage,
answer length and the oracle verdict. The answer text is stripped (it quotes
the project). `judged-<date>.jsonl`: the blind judge's YES/NO per run.

Reproduce the tables of a report from here:

```bash
python ../analyze.py results-2026-09-14.jsonl
```

`decomp.py` (price fit, first-call decomposition) needs the session
transcripts and cannot run from this directory.
