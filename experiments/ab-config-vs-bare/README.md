# A/B: your Claude Code configuration vs. bare

Does the pile of CLAUDE.md, auto-memory, hooks, plugins and `skillOverrides`
make Claude Code cheaper or more expensive, and does it change whether the
answer is right? This harness runs the same tasks through both arms in fresh
`claude -p` sessions and reads the bill from the transcripts.

The 2026-09-14 run on one real project is written up in
[../../report/ab-config-vs-bare.md](../../report/ab-config-vs-bare.md).
Its per-run numbers (no answer text) are in `data/`.

## Run it on your project

```bash
cp tasks.example.py tasks.py        # write 5-8 tasks from YOUR project, with oracles
python run.py --project /path/to/repo --reps 1 --dry      # see the plan
python run.py --project /path/to/repo --reps 3 --workers 3
python judge.py                     # blind Haiku for the tasks with a rubric
python analyze.py                   # per arm, per task, paired
python decomp.py                    # prefix write vs. the rest; recovers the prices
python export.py results.jsonl data/results-$(date +%F).jsonl   # shareable copy
```

What it costs: 8 tasks × 2 arms × 3 reps on Opus 5 was 48 sessions and
~US$12 API-equivalent (≈ US$0.25 per run). Runs are appended to
`results.jsonl` as they finish; a re-run skips what is already there.

## Design choices, and why

- **Fresh session per run.** The question is "what does the configuration
  add", and most of what it adds is injected at session start. A long
  session would amortise the prefix and hide the one cost that matters.
- **ABBA order, tasks shuffled with a fixed seed, 3 in parallel.** Removes
  time-of-day drift from the arm comparison; the seed makes the plan
  reproducible.
- **Both arms get `--strict-mcp-config` and `--dangerously-skip-permissions`.**
  In `-p` the desktop app does not inject MCP servers anyway; permissions
  would otherwise block one arm on a prompt the other does not see.
- **`bare` needs `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` on top of
  `--setting-sources ""`.** Probed before the run: without the env var the
  auto-memory directory is still loaded, so "bare" was not bare.
- **Deterministic oracles first, blind judge second.** Regex on the answer,
  `unittest` inside the fixture copy, or running the script the model wrote.
  The judge (Haiku, `--tools ""`, sees only the answer text) is for the one
  task where "did it refuse" is a judgment call, and as a cross-check on the
  regex tasks (12/12 agreement when we checked).
- **Tokens from the transcript, deduplicated by `message.id`.** The
  `--output-format json` usage block is per-iteration and Claude Code's
  `.jsonl` writes one line per content block; summing lines inflates ~1.7×.
- **Prices by regression, not from a price sheet.** `decomp.py` fits
  `total_cost_usd` against the five counters; residual 0 means the CLI's cost
  is exactly linear in them and the fitted numbers are the real multipliers.
  On 2026-09-14: input 5, 1h cache write 10, cache read 0.5, output 25 US$/M
  (all 48 writes were 1h; the 5m column was empty).
- **`bare` is not blind to the project.** It reads `CLAUDE.md` from disk when
  it decides to. What the test measures is the cost of *finding* what
  `config` receives injected — 3–4 calls versus 1.

- **Windows: `claude` resolves to `claude.cmd`, which goes through `cmd.exe`.**
  A prompt passed as an argument is parsed by cmd first, so `<`, `>`, `|`, `&`
  in it become redirections and the prompt arrives truncated — measured
  2026-09-15: the judge received the rubric only and nothing after `<<<`.
  `judge.py` therefore sends its prompt on stdin. `run.py` still passes the
  task prompt as an argument: keep those characters out of your `tasks.py`
  prompts on Windows, or set `CLAUDE_BIN` to the real `cli.js` via node.

## What it does not measure

Anything that acts *between* turns or *between* sessions: cache keep-alive,
handoff files, context-limit hooks, autocompact, MCP. The "fewer calls,
shorter answers" result transfers to long sessions; the prefix write cost
does not (it amortises). See the report for the break-even arithmetic.

## Files

| file | role |
|---|---|
| `run.py` | runs the plan, writes `results.jsonl` |
| `tasks.example.py` | template: prompt + fixture + oracle per task |
| `judge.py` | blind Haiku verdicts → `judged.jsonl`; `tasks.py` is looked up next to the results file first, then here |
| `analyze.py` | per-arm / per-task / paired summary |
| `decomp.py` | price fit + first-call-write vs. rest decomposition (needs the transcripts) |
| `export.py` | strips answer text for sharing |
| `data/` | exported runs from published experiments |

`runs/`, `results.jsonl`, `judged.jsonl` and `tasks.py` are git-ignored: they
carry your project's content.
