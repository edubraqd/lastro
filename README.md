# claude-context-forensics

Where the tokens go in Claude Code — measured on 641 real sessions — plus the
tools to measure your own and four hooks that act on what was found.

*Português: [LEIAME.md](LEIAME.md).*

## What was found

- **Cache reads are ~62% of the bill, cache writes ~30%, output ~8%.** The
  average call re-sends ~320k tokens; ~80k is the fixed prefix (system prompt,
  CLAUDE.md, tool schemas) and the rest is conversation history. Trimming
  CLAUDE.md moves ~2%. Session length moves everything.
- **80% of all cache writes come from a few large re-writes**, not steady
  growth: an idle gap over 60 min (the 1h TTL) breaks the cache 93–97% of
  the time; under 20 min, 1–7%. Resume and model switch re-write the whole
  history behind a 49k shared prefix. Changing the effort level mid-session
  re-writes it 31% of the time; a large share of the rest was a client bug
  that stopped reproducing after 2.1.237.
- **The session `.jsonl` overstates usage 1.7×** unless you dedup by
  `(message.id, requestId)` — one line per content block, same `usage` on each.
- `skillOverrides` saves 4.5% of the prefix (~2.7k tokens/call); plugin skills
  ignore it. `CLAUDE_CODE_COLD_COMPACT` is dead code in 2.1.270. Terse-output
  prompting cuts output 8%, and output is 8% of cost.

Full write-ups: [report/cache-forensics.md](report/cache-forensics.md) (filed
as [anthropics/claude-code#94177](https://github.com/anthropics/claude-code/issues/94177)),
[report/cache-forensics-followup.md](report/cache-forensics-followup.md), and
[report/findings.md](report/findings.md) for everything else with method and n.

## Measure your own sessions

Python 3.8+, stdlib only. Reads `~/.claude/projects/*/*.jsonl`; writes nothing.

```bash
python tools/sessions.py                 # per-session usage, dedup, cost split
python tools/sessions.py --last 0 --min-calls 5
python tools/breaks.py                   # cache breaks classified: ttl / prune / resume / ...
python tools/ttl.py --last 0             # break rate by idle gap
python tools/rewrites.py --last 0        # full re-writes with no gap: what changed before the history
python tools/diverge.py                  # proxy log: for each break, the first byte that differs from the call before
```

`tools/cache-proxy.py` is a local proxy that logs per-call usage from the API
response and (experimental) pings the API every 20 idle minutes to
keep the 1h cache warm (measured: a hit refreshes the TTL; 8/8 pings hit over 2h20). Launch through it with `tools/wrap-cache.sh` or
`tools/wrap-cache.ps1`. Read the docstring before using the keep-alive: each
ping costs a full cache read of the current context.

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
eviction from TokenPilot (arXiv 2606.17016). See findings §9.

Test: `python tests/test_hooks.py` (needs `node`; uses a temporary config dir,
touches nothing under `~/.claude`).

## Caveats

One user, one machine, mostly long sessions with the 1M window on. The shares
will differ for you; the mechanisms (TTL, prune, resume, jsonl duplication)
will not. Claude Code's source is not public: "microcompact" behaviour is
inferred from usage deltas and strings in the binary. Cost figures are
API-equivalent at list prices; subscriptions are accounted differently.

## License

MIT.
