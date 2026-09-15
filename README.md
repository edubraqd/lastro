# claude-context-forensics

Where the tokens go in Claude Code — measured on 674 real sessions and one
controlled A/B — plus the tools to measure your own, a cold ledger of what
each lever is actually worth, and four hooks that act on what was found.

*Português: [LEIAME.md](LEIAME.md).*

| start here | |
|---|---|
| [SAVINGS.md](SAVINGS.md) | every lever, its evidence, and its US$ on real logs — ceilings labelled as ceilings |
| [AUDIT.md](AUDIT.md) | where each number comes from and how to re-derive it from the raw transcripts |
| [AGENTS.md](AGENTS.md) | the operational summary for a coding agent: eight rules, one paste-able block |
| [report/](report/) | the write-ups with method and n |
| [experiments/](experiments/) | the A/B harness, with its raw runs |

## What was found

- **Cache reads are ~62% of the bill, cache writes ~30%, output ~8%.** The
  average call re-sends ~320k tokens; ~80k is the fixed prefix (system prompt,
  CLAUDE.md, tool schemas) and the rest is conversation history. Trimming
  CLAUDE.md moves ~0.2% per 1k tokens. Session length moves everything.
- **80% of all cache writes come from a few large re-writes**, not steady
  growth: an idle gap over 60 min (the 1h TTL) breaks the cache 93–97% of
  the time; under 20 min, 1–7%. Resume and model switch re-write the whole
  history behind a 49k shared prefix. Changing the effort level mid-session
  re-writes it 31% of the time. About half of the 80% was a client bug that
  stopped reproducing after 2.1.237.
- **A cache hit refreshes the 1h TTL, and a blind keep-alive pinger still
  loses money** (−0.8% over real idle gaps: most long gaps are overnight).
  Handoff + `/clear` before leaving is the version of that lever that pays.
- **A full configuration (CLAUDE.md + memory + hooks + overrides) was 100%
  vs 92% accurate, made 40% fewer calls, and cost US$0.10 more per
  one-task session** — the 21k prefix it writes on every new session, which
  is never served from another session's cache. Break-even ~3 tasks/session.
- **The session `.jsonl` overstates usage 1.7×** unless you dedup by
  `(message.id, requestId)` — one line per content block, same `usage` on each.
- `skillOverrides` saves 4.5% of the prefix (~2.7k tokens/call); plugin skills
  ignore it. `CLAUDE_CODE_COLD_COMPACT` is dead code in 2.1.270. The main
  thread is 1h-cached on 100% of writes and subagents 5m on 100%; the TTL
  settings do nothing useful here. Terse-output prompting cuts output 8%,
  and output is 8% of cost.

Write-ups: [report/cache-forensics.md](report/cache-forensics.md) (filed as
[anthropics/claude-code#94177](https://github.com/anthropics/claude-code/issues/94177)),
[report/cache-forensics-followup.md](report/cache-forensics-followup.md),
[report/findings.md](report/findings.md) (everything else, with method and n),
[report/ab-config-vs-bare.md](report/ab-config-vs-bare.md) (the A/B).

## Measure your own sessions

Python 3.8+, stdlib only. Reads `~/.claude/projects/*/*.jsonl`; writes nothing.

```bash
python tools/ledger.py                   # the SAVINGS table on your transcripts
python tools/sessions.py                 # per-session usage, dedup, cost split
python tools/sessions.py --last 0 --min-calls 5
python tools/breaks.py                   # cache breaks classified: ttl / prune / resume / ...
python tools/ttl.py --last 0             # break rate by idle gap
python tools/rewrites.py --last 0        # full re-writes with no gap: what changed before the history
python tools/first_call.py               # first call per session: what a warm start reads from other sessions (#94417)
python tools/diverge.py                  # proxy log: for each break, the first byte that differs from the call before
python tools/issues.py --top 40          # GitHub: claude-code issues on cache/context/cost, ranked by reactions (needs GITHUB_TOKEN or gh)
```

`tools/cache-proxy.py` is a local proxy that logs per-call usage from the API
response and keeps every request body (for `diverge.py`). Its keep-alive
ping is measured to refresh the TTL and measured to be net negative when run
blind — read findings §3 before switching it on. Launch through it with
`tools/wrap-cache.sh` or `tools/wrap-cache.ps1`.

## Run the A/B on your project

```bash
cd experiments/ab-config-vs-bare
cp tasks.example.py tasks.py             # 5-8 tasks from your project, with oracles
python run.py --project /path/to/repo --reps 3 --workers 3   # ~US$12 quota for 48 Opus runs
python judge.py && python analyze.py && python decomp.py
```

[experiments/ab-config-vs-bare/README.md](experiments/ab-config-vs-bare/README.md)
explains the design choices; `data/` holds the 48 runs of 2026-09-14.

## Hooks

Node.js, no dependencies. They act on the mechanisms above instead of on a
global token counter.

| hook | event | does |
|---|---|---|
| `context-guard.js` | UserPromptSubmit | reads the context of the last call from the transcript; above `CONTEXT_LIMIT` (200k) tells the model, every turn, to finish and ask for `/clear`. Records per-session peaks in `~/.claude/.context-peaks.json`. |
| `batch-eviction.js` | Stop | above `EVICTION_LIMIT` (150k), once per session, holds the stop and makes the model write a handoff to `<cwd>/.claude/handoff-<session>.md`. |
| `handoff-load.js` | SessionStart | after `/clear` or a new session, injects the newest handoff (< `HANDOFF_HOURS`, 12) and installs a **context canary**: a byte-stable first line (`**ctx · t<N> · ctx ok**`) that disappears when the instruction has fallen out of context. |
| `read-recovery.js` | PostToolUse (Read) | when a `Read` had a `limit`, tells the model how many lines remain and the offset to continue from. |

Install (references the checkout in place, so `git pull` updates them):

```bash
git clone https://github.com/edubraqd/claude-context-forensics
cd claude-context-forensics
python hooks/install.py --dry-run      # shows the resulting settings.json
python hooks/install.py                # ~/.claude/settings.json (backup kept)
python hooks/install.py --project .    # or a project's .claude/settings.json
python hooks/install.py --uninstall
```

Knobs, as environment variables or under `"env"` in settings.json:
`CONTEXT_LANG=pt` (Portuguese strings), `CONTEXT_LIMIT`, `EVICTION_LIMIT`,
`HANDOFF_HOURS`, `CANARY=0`, `CANARY_NAME`.

Why a handoff file and not `/compact`: a pruned history with a short summary
of what was done beat both the full history and a full-history summary on
cost, at equal or better accuracy, in Microsoft's "Less Context, Better
Agents" (arXiv 2606.10209). The canary is from
[JuliusBrussee/skills](https://github.com/JuliusBrussee/skills); batch
eviction from TokenPilot (arXiv 2606.17016). See findings §11.

A cost to know: a `UserPromptSubmit` hook that returns `additionalContext`
correlates with a full prefix re-write on 0.8% of user turns vs 0.06% without
(current versions). `context-guard.js` only speaks above the limit for that
reason.

Test: `python tests/test_hooks.py` (needs `node`; uses a temporary config dir,
touches nothing under `~/.claude`).

## Caveats

One user, one machine, mostly long sessions with the 1M window on. The shares
will differ for you; the mechanisms (TTL, prune, resume, jsonl duplication)
will not. Claude Code's source is not public: "microcompact" behaviour is
inferred from usage deltas and strings in the binary. Cost figures are
API-equivalent at list prices; on a subscription they are quota, not cash.
The A/B is n = 3 per cell on one project: it signs the direction of every
row, it does not size the effect for you.

## License

MIT.
