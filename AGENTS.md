# For the agent reading this repo

You are a coding agent (Claude Code or similar) and someone pointed you here
to cut Claude Code cost **without changing any code** — theirs or the
client's. This page is the operational summary. Everything on it is measured
in this repo; the numbers are in [SAVINGS.md](SAVINGS.md) and how to check
them in [AUDIT.md](AUDIT.md). Do not quote a saving that is not on those pages.

## What the bill is made of

On 674 real sessions: 62% cache reads (the conversation history re-sent on
every call), 30% cache writes (mostly a few large re-writes after a break),
8% output. The fixed prefix (system prompt, CLAUDE.md, tools) is ~80k of a
~320k average call. Configuration files move ~2%. Session shape moves the rest.

## Rules of behaviour that cost nothing and are measured

1. **Pick model, effort and fast mode before the long stretch.** Changing
   effort mid-session re-wrote the whole history 31% of the time; a model
   switch or `--resume` re-writes it every time behind a 49k shared prefix.
   Fast mode's header is in the cache key: first fast request re-reads all.
2. **Connect MCP servers and load skills at the start, not in the middle.**
   Tool-list, MCP and skill-listing changes re-wrote the prefix ~10% of the
   time each.
3. **Leaving for more than an hour with a large context? Write a handoff and
   `/clear` first.** Coming back after 60 min re-writes the history at 2×
   input price 93–97% of the time (760 events, US$3,076 API-equivalent on
   these logs). A handoff file + fresh session costs a ~30k write instead.
   Under 20 min, just come back (≤ 7% break rate).
4. **Do not run a blind cache keep-alive.** A pinger that fires every 20 min
   on every idle gap was net *negative* (−0.8%) over real behaviour because
   most long gaps are overnight. A hit does refresh the 1h TTL — that part is
   measured — so ping only when you know the person is coming back within 3 h.
5. **Abandon a bad path with `/rewind`, not `/compact`.** Rewind returns to
   a prefix already in cache and writes nothing.
6. **When you are the one writing the CLAUDE.md**: 1k tokens costs
   US$0.0005 per call (0.17% of a long session per 1k). Keep what the model
   needs on every turn; move history and decisions to a handoff file the
   session-start hook injects once. The `CLAUDE.md` block is never served
   from another session's cache — every new session writes it at 2×.
7. **Keep `skillOverrides` for skills you never use** (−2,752 tokens per
   call, 0.5% of the bill). Never set `workflow-authoring: off` (+17k chars).
   Plugin skills ignore the setting.
8. **Do not set `promptCacheTtl` or `subagentPromptCacheTtl`.** Main thread
   is already 1h on 100% of writes; forcing 1h on subagents costs more than
   the breaks it prevents. `CLAUDE_CODE_COLD_COMPACT` is dead code.

## What a full configuration is worth (so you can defend it)

Controlled A/B, 48 runs, Opus 5: CLAUDE.md + memory + hooks + overrides gave
100% vs 92% accuracy, 40% fewer calls, 40% less output, 60% less wall time,
and cost US$0.10 *more* per one-task session — the 21k prefix write. From ~3
tasks per session on, it is the cheaper arm. Do not strip a working
configuration to save the prefix; open fewer one-question sessions instead.
Details: [report/ab-config-vs-bare.md](report/ab-config-vs-bare.md).

## What you can measure for the person you work for

```bash
python tools/ledger.py            # their ledger: which lever touches what, on their logs
python tools/sessions.py          # per-session usage, deduplicated
python tools/ttl.py --last 0      # their break rate by idle gap
python tools/rewrites.py --last 0 # what changed before each full re-write
```

Stdlib only, read-only on `~/.claude/projects`. Run them before proposing
anything; the shares differ per person and the ledger tells you which lines
are worth their attention.

## If they want the hooks

`python hooks/install.py --dry-run` shows the resulting settings.json;
without `--dry-run` it installs four hooks (context guard, batch eviction,
handoff load with a context canary, read recovery) referencing this checkout.
`--uninstall` reverts. See the README for the knobs. The hooks implement
rules 3 and 6 mechanically; they do not change any code.

## A block you can paste into a project's CLAUDE.md

```markdown
## Context cost (measured; see github.com/edubraqd/lastro)
- Pick model, effort and fast mode at session start; never switch mid-session.
- Connect MCP / load skills before the long stretch.
- Away > 1 h with a big context: write a handoff, then /clear. < 20 min: just come back.
- Abandon a path with /rewind, not /compact.
- No blind keep-alive pinger; no promptCacheTtl settings.
```

Five lines, ~90 tokens. That is the whole actionable content of this repo for
day-to-day work; the rest is evidence.
