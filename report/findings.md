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

On the hits, `cache_read / previous context` has median 1.0003: the prefix
is byte-stable across an idle turn. Below 60 min the re-writes that do happen
grow with the gap (8% → 25%) and not with context size (8–11% in every band
from 50k to 1.1M), and what survives is always the shared system+tools block
only — that looks like eviction of the conversation blocks ahead of TTL,
not client-side drift.

**Keep-alive, measured.** `tools/cache-proxy.py` stores the last streaming
`/v1/messages` body and, after 20 min idle, replays it with `stream: false,
max_tokens: 1` every 20 min. One `claude -p` session, Opus 5, 1h cache,
`thinking: adaptive` (accepted `max_tokens: 1`), 2026-09-14:

```
00:28:30 real   cc 13,602  cr 34,453  out 22     <- the write
00:28:36 ping   cc 0       cr 48,055  out 1
00:49:03 ping   cc 0       cr 48,055  out 1      idle 21 min
01:09:04 ping   cc 0       cr 48,055  out 1      idle 41
01:29:06 ping   cc 0       cr 48,055  out 1      idle 61   <- past the original TTL; hit only because 01:09 refreshed it
01:49:07 ping   cc 0       cr 48,055  out 1      idle 81
02:09:08 ping   cc 0       cr 48,055  out 1      idle 101
02:29:09 ping   cc 0       cr 48,055  out 1      idle 121
02:49:11 ping   cc 0       cr 48,055  out 1      idle 141
```

48,055 = 13,602 + 34,453. Eight pings, 8 output tokens, zero cache writes,
OAuth headers still valid at 2h20. **A cache hit refreshes the 1h TTL.** Each
ping costs 0.1× of the current context; against a TTL re-write at 2× the
break-even is ~20 pings, i.e. ~7 hours of idle per event. Posted as a
[comment on #94177](https://github.com/anthropics/claude-code/issues/94177#issuecomment-5662890763).

**Aggregated over real behaviour it is a wash (added 2026-09-15).** The
per-event arithmetic above assumes you come back. `tools/ledger.py` replays a
blind pinger over every idle gap in the 674 sessions — it pays a ping every
20 min on every gap, break or not, up to 9 per gap — and credits it only the
TTL re-writes it would have reached:

| pinger | TTL breaks reached | pings paid | net |
|---|---|---|---|
| blind, 9 pings max (3 h) | 324 of 760 | on every gap > 20 min | **−US$338 (−0.8%)** |
| blind, 6 pings max | 262 | | −US$220 (−0.5%) |
| blind, 3 pings max | 91 | | −US$382 (−0.9%) |
| pings only on sessions you knew you'd return to within 3 h | 324 | only those | +US$880 (+2.2%) |

Of the 760 TTL re-writes, 436 came after a gap over 200 min (267 over 8 h —
overnight); the pinger had already given up, and its pings on those gaps were
pure cost. The gross ceiling — every TTL re-write avoided for free — is
US$3,076 (7.6%); the honest number for a pinger that does not know when you
come back is zero or slightly negative. What does capture the 7.6% without a
pinger: a handoff file and `/clear` before leaving, which costs a ~30k prefix
write on return instead of a ~400k history re-write.
Two pitfalls if you rebuild it: the Haiku side-call (title / classifier)
arrives ~1 s after the main call and must not be the body that gets replayed;
on Windows `SO_REUSEADDR` lets two listeners bind the same port.

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

### 4.1 The `partial` bucket, opened (`python tools/rewrites.py --last 0`)

1,209 of the 1,336 `partial` events (99% of their tokens) have `cache_read`
equal to the **shared** prefix (48,193 / 47,285 / 24,247 depending on the
version) while the context did not shrink: the history was intact but not
reusable, so whatever sits *before* it — the project part of the system
prompt, tool schemas, request parameters, or the first message — changed
between two consecutive calls. Over all 132,016 call boundaries with no gap,
no model switch and no shrink, this happens 0.9% of the time. Where:

| boundary | n | full re-write | rate |
|---|---|---|---|
| after a **user turn** (previous call ended with text) | 82,342 | 1,118 | **1.4%** |
| after a tool call | 49,674 | 102 | 0.2% |

The new user turn is where the client re-renders the prefix. Events found in
the transcript between the two calls, and the re-write rate when present:

| event between the calls | n | rate |
|---|---|---|
| `ultra_effort_enter` (effort level changed) | 169 | **30.8%** |
| `deferred_tools_delta` (tool list changed) | 622 | 10.6% |
| `mcp_instructions_delta` (MCP server (re)connected) | 421 | 10.2% |
| `skill_listing` (skills list changed) | 232 | 9.5% |
| `hook_additional_context` (a hook injected context) | 5,877 | 8.3% |
| `model_refusal_fallback` | 22 | 77% |
| baseline (any boundary) | 132,016 | 0.9% |

The first four change the request prefix by construction (parameters, tool
schemas, system prompt), so those 161 events (65M tokens) have a visible
cause. **Changing effort mid-session is the one that costs the most per
event** and is the easiest to avoid: pick the effort before the long session.
The hook correlation survives the controls. Restricting to user turns
(the hook only fires there), dropping every boundary with a known prefix
event and the two outlier sessions of the next paragraph:

| user-turn boundary | n | re-wrote | rate |
|---|---|---|---|
| a `UserPromptSubmit` hook injected context — all versions | 4,500 | 264 | **5.87%** |
| no hook context — all versions | 70,089 | 203 | 0.29% |
| hook — 2.1.237 and later | 1,489 | 12 | 0.81% |
| no hook — 2.1.237 and later | 32,962 | 19 | 0.06% |

20× overall, 13× on current versions, spread over 10+ sessions (0–28% per
session). Mechanism unknown: the injected text is an attachment to the user
message and should sit after the cached history; yet ~1 user turn in 120 on
current versions re-writes the whole prefix when a hook has spoken. If you run
`UserPromptSubmit` hooks that return `additionalContext` (this repo's
`context-guard.js` does, only above the limit), this is a cost to know about.
To find the mechanism, run a session through `tools/cache-proxy.py` (it now
keeps every request body) until a break lands, then `tools/diverge.py`
prints the first byte that differs from the call before, in cache order.
Not done yet: the proxy log had no break at the time of writing.

The remaining 1,059 events (502M tokens) have nothing in the log between the
calls that should touch the prefix. They are **concentrated by version and
by session**, which points at client bugs, not at anything the user did:

| Claude Code version | boundaries | re-wrote | rate |
|---|---|---|---|
| 2.1.215 | 1,288 | 419 | **32.5%** |
| 2.1.170 | 1,838 | 56 | 3.0% |
| 2.1.181 / 2.1.202 / 2.1.209 | 15,763 | 283 | 1.8% |
| 2.1.197 / 2.1.227 / 2.1.177 | 7,210 | 94 | 1.3% |
| 2.1.219 / 2.1.221 / 2.1.205 | 18,335 | 156 | 0.9% |
| 2.1.229 / 2.1.222 | 19,060 | 94 | 0.5% |
| **2.1.237 and later** | **60,000+** | **71** | **0.1–0.2%** |

One session on 2.1.215 (Sonnet 5, 992 calls, 16 h, July 2026) holds 417
of them: from call 496 at ~566k context to the end, nearly every call
re-wrote ~520k with only the 48k shared prefix cached — 216M tokens in one
session. The only transcript line between the last cached call and the
first re-written one is a `custom-title` update. A second session (2.1.181,
8,807 calls) holds 130, most at ~990k context. Whatever it was, it is gone
after 2.1.237: 36 unexplained events in 60k+ boundaries, 11.9M tokens.

Rate also rises with context size (0.4% under 200k → 1.9% at 500–800k).
Without the two outlier sessions the slope flattens to 0.39% → 0.95% but does
not vanish, in both eras (old 0.69% → 1.27%; current 0.11% → 0.21%).

What this changes in the numbers above: of the 80% of writes attributed to
breaks, roughly half came from an old-version client bug that no longer
reproduces; TTL (26%) and resume (6%) are the mechanisms that remain. For a
current user the actionable list is: idle > 60 min, resume, model switch,
effort change, MCP reconnect mid-session, and hooks that inject context on
every prompt.

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

## 9. The `CLAUDE.md` block is never shared across sessions

The docs say sessions in the same directory "build matching prefixes and read
each other's cache", and the caching blog lists `CLAUDE.md` as "cached within
a project". Measured on the first call of every session (`tools/first_call.py`,
703 sessions, 2026-09-14): a warm start (< 60 min after another session in
the same directory) reads **46,328** tokens from cache in every project —
the tool schemas plus `system[0..2]` — plus a fixed 3.4–6.2k per project
(`system[3]`, which carries the memory path). **Zero of 474 warm starts read
the `CLAUDE.md` block** from another session's cache.

Why (request bodies captured through the proxy, CLI 2.1.270): the order on
the wire is `tools → system[0..3]` (cache breakpoints on 2 and 3) → `msg0 =
user [CLAUDE.md + MEMORY reminder | userEmail | attribution | PROMPT]` →
`msg1 = system (cache_control)` with hooks, environment (scratchpad uuid),
deferred tools, agents, MCP, skills. No breakpoint sits at the end of the
`CLAUDE.md` block; the next one is in `msg1`, *after* the user prompt. Two
sessions diverge at the prompt, so nothing after `system[3]` can match. The
scratchpad uuid in the environment block is irrelevant — the prompt already
differs before it. Filed as
[#94417](https://github.com/anthropics/claude-code/issues/94417).

Weight: 4–7k tokens (`CLAUDE.md`) to 21k (a full project prefix with memory
and hook text, [ab-config-vs-bare](ab-config-vs-bare.md)) per new session at
2× write price — US$0.05–0.21 per session. Under 0.2% of a long session; the
only regime where it matters is many one-question sessions.

## 10. TTL buckets: the main conversation is always 1h, subagents always 5m

The docs (`code.claude.com/docs/en/prompt-caching`, read 2026-09-14) describe
two buckets per request: main conversation 1h on a subscription within quota
(5m in overage), subagents / workflows / compaction / titles 5m; knobs
`promptCacheTtl`, `subagentPromptCacheTtl` (≥ 2.1.242), `FORCE_PROMPT_CACHING_5M`.
The transcript records `usage.cache_creation.ephemeral_5m_input_tokens` and
`_1h_`, so this is checkable (`tools/ledger.py`, "cache writes by TTL bucket"):

| thread | 1h writes | 5m writes |
|---|---|---|
| main conversation | 1,196.6 M | 0.02 M (one session in July) |
| subagents (`isSidechain`) | 0 | 92.5 M |

Consequences: this account was never in overage, so `promptCacheTtl` would
change nothing — do not set it. Gaps ≥ 5 min in subagents break 81–100%, but
there are only ~390 such gaps; forcing 1h there would raise 372M tokens of
5m writes (1.25×) to 1h writes (2×) for a saving smaller than the surcharge —
do not set `subagentPromptCacheTtl: 1h` either. And the break-rate curve of
section 3 (8% at 5–20 min rising to 24% at 40–60) is measured on 1h writes
only; it is not a 5m bucket in disguise. The literature explanation is
server-side eviction ahead of TTL under load (Continuum, arXiv 2511.02230 §1;
SAECache, arXiv 2605.18825 §2.2): a 1h TTL is a ceiling, not a guarantee.

Also from the same doc, matching the logs: changing effort mid-session
invalidates on Opus 5 (only Fable 5.1 ≥ 2.1.260 preserves it); fast mode
puts a header in the cache key, so the first fast request re-reads everything
— switch it on at the start, never mid-session; `/rewind` returns to a cached
prefix and writes nothing; a warm `/compact` reads the prefix and only
generates the summary, a cold one (> TTL) reprocesses everything.

## 11. Reading list that shaped the hooks

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
