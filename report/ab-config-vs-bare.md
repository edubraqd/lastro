# A/B: a full Claude Code configuration vs. bare (2026-09-14)

**Question.** Does the accumulated configuration — global and project
`CLAUDE.md`, auto-memory, a terse-output plugin with its hooks, four context
hooks, `skillOverrides`, a skills plugin, env limits — change cost and
accuracy against Claude Code with none of it?

**Answer, in one line.** Accuracy 24/24 vs 22/24, 40% fewer API calls, 40%
less output, 60% less wall time — and **more expensive in 24 of 24 paired
runs**, by US$0.10 per run, entirely because the configured session writes a
21k-token prefix into the cache at 1h-write price on every new session. Below
about three tasks per session the bare arm is cheaper; above it, the
configured one is.

Harness and per-run data: [experiments/ab-config-vs-bare](../experiments/ab-config-vs-bare/).

## Method

- `claude -p` 2.1.272, `claude-opus-5`, same project directory, **fresh session
  per run**, `--strict-mcp-config` and `--dangerously-skip-permissions` in both
  arms, `CANARY=0` in both (the canary only means something across sessions).
- **bare**: `--setting-sources ""` + `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`.
  Probed first: without the env var the auto-memory still loads.
- **config**: `--setting-sources user,project,local`, everything as in daily use.
- 8 tasks × 2 arms × 3 repetitions = **48 runs**, ABBA order per task, tasks
  shuffled (seed 42), 3 runs in parallel. Zero errors, zero timeouts.
- Oracles: deterministic on 7 tasks (regex on the answer, `unittest` in a
  fixture copy, executing the script the model wrote); a blind judge (Haiku,
  isolated, sees only the answer text) on the one task where "did it refuse"
  is a judgment. The judge also re-graded two regex tasks: 12/12 agreement.
- Tokens read from the session transcript, deduplicated by `message.id`.
  Prices recovered by least squares on the CLI's own `total_cost_usd`
  (residual 0): input 5, **1h cache write 10**, cache read 0.5, output 25
  US$/M. All 48 first-call writes were 1h.

The tasks, in kind: (t1) an operational fact that lives in `CLAUDE.md`;
(t2) a request that violates a documented, load-bearing project rule;
(t3) two injected bugs in a copy of a module, tests must pass; (t4) a count
over a data file; (t5) "where in the code does X happen"; (t6) write a small
CLI script to a spec and run it; (t7) a value that is *empty* in the data —
does it say so or invent a number; (t8) "why was design decision D taken".

## Result

| | bare | config |
|---|---|---|
| accuracy | 22/24 (92%) | **24/24** |
| API calls per run (median / mean) | 3 / 4.0 | **2 / 2.4** |
| context read + written per run | 121k / 179k | **109k / 139k** |
| cache write on the first call | 5.2k | 21.0k |
| output tokens | 867 / 1,393 | **502 / 844** |
| answer length (chars) | 366 / 883 | **216 / 496** |
| wall time (s) | 19 / 46 | **14 / 19** |
| **US$ per run** | **0.176 / 0.206** | 0.277 / 0.306 |

Paired by (task, repetition), 24 pairs: config more expensive in **24/24**,
shorter in 21/24, fewer calls in 19/24.

Where bare failed: t2 twice — it delivered the rule-breaking script with a
generic warning and no reference to the project rule; on the third repetition
it happened to read `CLAUDE.md` from disk and cited the rule. Config refused
or warned 3/3, citing the rule and the concrete risk. (A third apparent bare
failure on t5 was an oracle bug: a second, legitimate location for the same
behaviour; the oracle was corrected and the run counted as correct.) Re-judged on
2026-09-15 with the shipped `judge.py` (same rubric, same model, fresh calls):
5/6 verdicts identical; bare r1 flipped NO → YES. Judge noise of one run in
six is the resolution of this test — read the t2 row as "bare 1–2 of 3, config
3 of 3", not as an exact count.

### Cost decomposition

| per run, mean | bare | config |
|---|---|---|
| prefix write on call 1 | 5.2k tok = US$0.05 | 21.0k tok = **US$0.21** |
| cost of calls 2..n | 0.130 | **0.067** |
| calls beyond the first | 3.4 | 1.5 |
| cost per call, 2..n | 0.038 | 0.046 |
| cache read per call | 40k | 57k |
| **cost without the prefix write** | 0.154 / median 0.125 | **0.096 / median 0.066** |

Without the first-call write, config is cheaper in 19/24 pairs (−38% on the
mean).

What the number says: **the whole cost difference is the project prefix
(`CLAUDE.md` + memory + hooks + skills listing, ~21k tokens) written to the
cache on every new session at 1h-write price, 2× input.** That block is never
served from another session's cache
([findings §9](findings.md#9-the-claudemd-block-is-never-shared-across-sessions),
703 sessions, [#94417](https://github.com/anthropics/claude-code/issues/94417)).
Break-even: US$0.16 of extra write against US$0.058 saved per task → **from
~3 tasks per session on, the configured arm is cheaper**; a one-question
session is cheaper bare. In the real sessions on this machine (52–720 calls,
mean context 320k) the prefix is noise and the call count is what matters:
here config made 40% fewer.

## What this test does not measure

Short sessions, no history. Out of scope: the cache keep-alive proxy (between
turns), the canary/handoff hooks (between sessions), the Stop-hook eviction
at 180k, autocompact, MCP servers (absent in both arms). "Fewer calls" and
"shorter answers" transfer to long sessions; the prefix cost does not (it
amortises).

The bare arm is not blind to the project: it reads `CLAUDE.md` from disk when
it decides to (t1, t8, t2 r3). The test measures the cost of *finding* what
the configured arm receives injected — 3–4 calls versus 1.

One user, one project, 8 tasks, n = 3 per cell. Enough to sign the direction
of every row (24/24, 21/24, 19/24 paired); not enough to put a tight interval
on the size of the effect. Rerun on your project before quoting the
percentages as yours.

## Verdict

Worth it, with a session-size caveat. The two bare failures are on the one
rule whose violation has real-world consequences; the accuracy gain is not a
rounding error. The single downside is a 21k-token write per new session, and
it is not a cost of the modifications as such — it is `CLAUDE.md` not being
cacheable across sessions. The remaining lever is the size of that prefix
(this project's `CLAUDE.md` is 20.5k chars; part of its history could live in
a handoff file) or opening fewer new sessions per day. Removing the hooks or
the terse-output plugin does not move this number: the bulk is text.

## Reproduce

```bash
cd experiments/ab-config-vs-bare
cp tasks.example.py tasks.py            # your tasks
python run.py --project <your repo> --reps 3 --workers 3     # ~US$12 of quota for 48 runs
python judge.py && python analyze.py && python decomp.py
```
