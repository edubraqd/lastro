# Findings — everything measured, with method and n

One user, one machine (Windows 11, Claude desktop app + CLI, Claude Code
2.1.266–2.1.270, Opus 5 / Fable 5.1 / Haiku 4.5, 1M context on), September
2026. Every number below has the command that produced it. Shares will differ
for other users; the mechanisms should not.

The main report is [cache-forensics.md](cache-forensics.md) (30 sessions,
filed as [anthropics/claude-code#94177](https://github.com/anthropics/claude-code/issues/94177))
with a [follow-up](cache-forensics-followup.md) that cross-references
[#42542](https://github.com/anthropics/claude-code/issues/42542). This file
collects the rest.

## 1. The session `.jsonl` overstates usage 1.7× unless you dedup

Claude Code writes one `assistant` line per content block (thinking / text /
tool_use). Every line of the same API call carries the same `usage`. Summing
per line: 5,568 lines; deduplicated by `(message.id, requestId)`: 3,203 calls.

Any cost tool built on the logs is over-counting unless it dedups. A resumed
or forked session also copies the whole transcript into a new file, so the
same calls appear twice across files — `tools/sessions.py` dedups across every
file read in one run.

## 2. Where the money goes: history, not the prefix

All-time view (`python tools/sessions.py --last 0 --min-calls 5`, 2026-09-14):

| | tokens | share of API-equivalent cost |
|---|---|---|
| cache_read | 49.9 B | 62% |
| cache_creation | 1.19 B | 30% |
| output | 132 M | 8% |
| input (uncached) | 4.7 M | 0% |

641 sessions, 133,824 calls. First call of a session: `cache_creation` median
28,950, `cache_read` median 38,099, cold start (`cache_read` = 0) in 10/641.

The 30-session sample in the main report gives 64 / 28 / 9. Same picture:
**the prefix (system prompt + CLAUDE.md + tool schemas, ~80k) is a quarter of
an average call; the conversation history is the rest.** Trimming CLAUDE.md
(~6k of ~320k per call) is not a lever. Session length is.

## 3. An idle gap ≥ 60 min breaks the cache almost always; < 20 min almost never

`python tools/ttl.py --last 0` (641 sessions, pairs of consecutive calls with
previous context ≥ 20k):

| gap between calls | pairs | re-wrote the history | rate |
|---|---|---|---|
| 0–2 min | 123,083 | 863 | 1% |
| 2–5 | 4,973 | 213 | 4% |
| 5–10 | 2,206 | 152 | 7% |
| 10–20 | 1,198 | 79 | 7% |
| 20–30 | 401 | 51 | 13% |
| 30–45 | 266 | 46 | 17% |
| 45–60 | 124 | 25 | 20% |
| 60–90 | 131 | 127 | **97%** |
| 90–180 | 175 | 170 | **97%** |
| > 180 | 479 | 444 | **93%** |

The documented 1h TTL shows up as a cliff at 60 minutes. Below it the rate
climbs slowly — those are the prunes, resumes and skill loads of section 4,
not the TTL. Practical rule: if you are stepping away for more than an hour on
a large context, `/compact` or write a handoff and `/clear` before you go;
coming back re-writes the whole history at 2× write price.

`tools/cache-proxy.py` has an experimental keep-alive (re-send the last body
with `max_tokens=1` every 20 min of idle). Each ping is a full cache read
(0.1×) of the current context, so it only pays if you come back. Not measured
end-to-end yet; the log it writes is what you would measure it with.

## 4. Cache breaks by cause

`python tools/breaks.py --last 0` (641 sessions). A "break" is a call whose
`cache_creation` exceeds 20% of the previous context and 20k tokens.

| cause | events | tokens written | share of all writes |
|---|---|---|---|
| ttl (gap > 60 min) | 745 | 306 M | 26% |
| resume / model switch | 161 | 66 M | 6% |
| prune (context shrank ≥ 30%, no gap) | 4 | 1.0 M | 0% |
| compact summary | 1 | 0.5 M | 0% |
| cold (cache_read = 0, no gap) | 11 | 4.9 M | 0% |
| partial (cache_read > 0, none of the above) | 1,336 | 570 M | 48% |
| **all breaks** | 2,258 | 949 M | **80%** |

Median re-write 431k tokens, max 980k.

The `partial` bucket is the honest gap in this classification: something
after the shared prefix changed with no idle gap, no model change and no
visible shrink. The 30-session report identified four of those as
microcompact events (tool results cleared in place, `cache_read` collapsing to
the shared prefix). Over 641 sessions the bucket is too large to be only that;
skill loads, `cache_edits`, and the system prompt changing mid-session are all
candidates. Not analysed further. If you dig into it, `breaks.py --top 50`
gives you the call numbers.

## 5. `skillOverrides` per project: real, small (−4.5% of the prefix)

Hiding skills in `.claude/settings.json`:

```json
{ "skillOverrides": { "some-skill": "off", "other-skill": "off" } }
```

Measured 2026-09-14, `claude -p "reply only: ok" --max-turns 1`, ABABAB,
n = 3 per arm, settings file renamed between arms:

| | total input tokens (1st call) |
|---|---|
| without overrides | 60,781 (± 1) |
| with 28 overrides | 58,029 (± 2) |
| **delta** | **−2,752 (−4.5%)** |

Desktop app, observational, same day: first-call `cache_creation` 33,444–34,073
before (n = 5) vs 31,047 after → −2,770. Two methods converge.

What it does and does not do:

- Works for user skills (`~/.claude/skills`) and built-ins: 35 → 24 in the
  listing, 13.0k → 7.0k chars.
- **Does not work for plugin skills** (`superpowers:*`, `anthropic-skills:*`):
  neither `plugin:skill` nor `skill` matches. Only `enabledPlugins` removes
  them. 14 of the 28 entries in my file are no-ops for that reason.
- **Never set `workflow-authoring: off`**: the `Workflow` tool then inlines
  the whole reference in its description, +17k chars.
- `/context` does not show the saving
  ([#94174](https://github.com/anthropics/claude-code/issues/94174)); measure
  with `tools/sessions.py` (first-call `cache_creation`).
- Weight in practice: it only touches the fixed prefix. In a 52-call session
  that is ~1.9% of cost; in a 720-call session, 0.4%. Keep it (free), but it
  is not where the money is.

## 6. `CLAUDE_CODE_COLD_COMPACT` is dead code in the local CLI (2.1.270)

The name suggests "compact when the cache is already cold", which would be the
right feature (section 5.1 of the main report). Reading the binary:

- `ptr()` computes `D = !stripNonEssential && tengu_compact_cache_prefix`: the
  flag only makes the autocompact **summary leaner** and, when on, sends that
  summary **without** the cache prefix — worse in the warm case (1× write
  instead of 0.1× read).
- `E_s()`: `if (isLocal() && autoWindow) return false` — with the default
  window the client-side threshold never runs, no `autocompact:` line is ever
  logged. With a window set via env/settings the path goes through
  `routing through reactive`, which does not read the flag. It is only
  reachable with `CLAUDE_CODE_REMOTE` or without the reactive handler.
- A/B forcing compaction (`CLAUDE_CODE_AUTO_COMPACT_WINDOW=100000`, n = 1 per
  arm): ON and OFF token-identical (compact input 25,837 uncached, `cache_read`
  ~57.8k, `cache_creation` 127–162).
- Haiku with the automatic window at 181k context: zero `autocompact:` lines,
  confirming the early return.

Removed from my settings. Do not set it expecting cache-aware compaction.

### Recipe to force a compaction in `claude -p` (for measuring)

```bash
CANARY=0 CLAUDE_CODE_AUTO_COMPACT_WINDOW=100000 \
  claude -p "Read <file of ~22k tokens> then say ok" --debug-file dbg.txt --max-turns 3
grep "reactive-compact" dbg.txt      # 'Forked agent [reactive-compact] finished: ... totalUsage:'
```

Minimum window is 100k (effective ~80k). `Read` caps at 25k tokens per call;
pt-BR text is ~2.3 chars/token. The jsonl does **not** record the compaction
agent's usage; only `--debug-file` has it. On Git Bash, `MSYS_NO_PATHCONV=1`
keeps `/compact` from being turned into a path. `--resume` re-writes the prefix
(25,198 vs 23,381 tokens): it is not byte-stable across sessions.

## 7. "Caveman" terse-output prompting: −8% output, and output is 8% of cost

The [caveman](https://github.com/JuliusBrussee/caveman) plugin asks the model to
answer in compressed English. Measured in pt-BR, Haiku 4.5, 10 developer
prompts × 2 rounds, `claude -p` isolated (`--setting-sources "" --disable-slash-commands --tools "" --strict-mcp-config`):

| baseline | caveman effect on output tokens |
|---|---|
| a terse "how to work with me" CLAUDE.md | **−8%** (median −5%, sd 25%) |
| `"Answer concisely."` only | +19% |

Zero drift to English in 30 replies. Since output is 8–9% of API-equivalent
cost, an 8% cut on it is ~0.7% of the bill. The measurement script and pt-BR
prompts are in [JuliusBrussee/caveman#1044](https://github.com/JuliusBrussee/caveman/pull/1044).

The same project ships a proxy that compresses tool output on the wire. Its
own benchmark claims −33% input tokens; my A/B is running
(`tools/ab-route.py`) and is not decided yet. Two warnings from that setup:
launch with `caveman wrap claude` only — `caveman enable` writes
`ANTHROPIC_BASE_URL` into settings.json and the desktop app / Remote Control
stop working without the proxy up; and a compressor that rewrites *history*
breaks the cache prefix on every call, which costs more than it saves
(TokenPilot, below).

## 8. A proxy is for reading the request body, not for measuring cost

`claude -p` with `ANTHROPIC_BASE_URL` set sends **all 139 tool schemas without
deferral** (418k chars): total 184k tokens vs 60k direct. Use the proxy to see
what is in the prompt; use the jsonl (`tools/sessions.py`) to count.
`_CLAUDE_CODE_ASSUME_FIRST_PARTY_BASE_URL=1` keeps the 1M window through a
loopback proxy; whether it also restores tool deferral was not tested.

## 9. Reading list that shaped the hooks

- **TokenPilot** (arXiv 2606.17016). Cost K = α·hit + miss; text compressors
  (LLMLingua-2, SelectiveContext) cost *more* than vanilla in continuous mode
  because they break the prefix; stable placeholders take hit rate 38.7 → 79.2%;
  batch eviction (B = 3) is the optimum. → `hooks/batch-eviction.js`.
- **Less Context, Better Agents** (Microsoft, arXiv 2606.10209). Keep the last
  N tool results verbatim + a running summary beats both full history and
  full-history summary on cost; pruning kills stale-state errors (34 → 6) but
  triples premature termination (9 → 18); the summary brings it back (18 → 3).
  → the handoff file is that summary.
- **Total Recall at What Cost** (arXiv 2608.11879). Full history: cost per turn
  ∝ size × depth → quadratic cumulative; rolling window q ≈ 0.1. Memory
  systems (Mem0, Hindsight, Mastra) are not predictable from (N, L): 18–69%
  held-out error, up to 3.3× the transcript.
- **Inside the Scaffold** (arXiv 2604.03515, §4.3.2). SWE-agent `polling`
  changes truncation only every k steps to keep the prefix; OpenCode prunes
  tool output beyond the last 40k before summarising.
- **Context canary**: [JuliusBrussee/skills](https://github.com/JuliusBrussee/skills)
  `context-canary` — a byte-stable first line that disappears when the
  instruction has fallen out of context. → `hooks/handoff-load.js`.
