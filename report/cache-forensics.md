# Prompt-cache forensics from 30 real Claude Code sessions — where the cache writes come from, and what the literature suggests

*Measured 2026-09-13 by one user (Windows 11, Claude desktop app, Claude Code 2.1.266, Opus 5 / Fable 5.1, 1M context enabled). Filed as [anthropics/claude-code#94177](https://github.com/anthropics/claude-code/issues/94177). Reproduce with [`tools/sessions.py`](../tools/sessions.py) and [`tools/breaks.py`](../tools/breaks.py).*

## TL;DR

- Across 30 sessions (3,203 API calls), **cache reads are 64% of API-equivalent cost**, cache writes 28%, output 9%. Average context per call is **320k tokens** (median 239k, p90 707k). The system-prompt prefix is ~83k of that (49k shared across projects + ~34k project-specific); **the rest is conversation history**.
- **68% of all cache-write tokens (14.8M of 21.7M) come from 36 events**, not from steady-state growth. Three causes, all client-observable:
  1. **1h TTL expiry** — 19 events, 9.4M tokens. Expected, but each one re-writes 300–860k of history.
  2. **Mid-history pruning (microcompact)** — 4 events in one session, 3.0M tokens. Each time ~83k of old tool results were cleared, `cache_read` fell to the shared prefix (47,638) and 620–830k were re-written. Once it happened **two calls after** a TTL re-write: 1.3M tokens written inside one minute, where a prune aligned to the cold miss would have cost nothing extra.
  3. **Resume / model switch** — ~6 events, ~1.9M tokens. On resume `cache_read` equals the *shared* prefix only (49,043), so the project part of the system prompt is not byte-stable across sessions and the whole history is re-written behind it.
- The suggestions below are small and mostly scheduling: prune when the cache is already cold, prune in bigger batches, keep the project prefix byte-stable on resume, and consider a bounded-history default. Each has a paper behind it (section 4).
- A measurement pitfall worth documenting: **the session `.jsonl` writes one `assistant` line per content block (thinking / text / tool_use), each carrying the same `usage`.** Summing usage per line overstates everything ~1.7×. Dedup by `(message.id, requestId)`.

## 1. Method

- Source: `~/.claude/projects/*/*.jsonl`, the 30 most recently modified sessions (25 with ≥5 calls). Only `type == "assistant"` entries with `message.usage`.
- Dedup by `(message.id, requestId)` → 5,568 lines become 3,203 calls.
- "Cache break" = a call whose `cache_creation_input_tokens` exceeds 20% of the previous call's total context and 20k tokens. Classified by wall-clock gap to the previous call (>60 min → TTL), by whether the context shrank, and by what happened between the two calls (tool used, `<synthetic>` model marker, model id change).
- Cost is *API-equivalent* at Opus-class list prices ($5/M input, $25/M output, cache read 0.1×, 1h cache write 2×). The user is on a subscription; the dollar figures only rank the levers. With 5-minute-write pricing (1.25×) the write share drops from 28% to 19% and the conclusions do not change.

## 2. Findings

### 2.1 Totals (30 sessions, deduplicated)

| | tokens | API-equiv | share |
|---|---|---|---|
| cache_read | 1,003,906,966 | $502 | 64% |
| cache_creation | 21,702,482 | $217 | 28% |
| output | 2,761,619 | $69 | 9% |
| input (uncached) | 35,166 | ~$0 | 0% |

Context per call: mean 320,213 · median 238,633 · p90 706,564. One session (`dd75af27`, 720 calls) alone read 384M tokens.

### 2.2 Prefix composition

First call of a session: `cache_creation` median **34,296**, `cache_read` median **44,776** (49,043 on most). The read part is identical across projects — system prompt plus built-in tool schemas, served from a still-warm 1h cache. The written part is the project layer (CLAUDE.md ≈ 6k, memory index, skills list, MCP tool schemas, hook output). 4 of 30 sessions started fully cold (`cache_read 0`, ~85–93k written).

So the prefix is ~26% of the average context and CLAUDE.md is ~2%. Trimming CLAUDE.md is not a lever; history size is.

### 2.3 Where cache writes come from

| cause | events | tokens written | share of all writes |
|---|---|---|---|
| TTL expiry (gap > 60 min) | 19 | 9,432,054 | 43% |
| mid-history prune, same model, no gap | 4 | 2,974,035 | 14% |
| resume / model switch (`<synthetic>` → model, Fable ↔ Opus) | ~6 | ~1.9M | ~9% |
| skill load (`cache_read` intact, write = skill body: 21k–41k) | several | small | legit |
| everything else (normal turn-by-turn growth) | 3,160+ | ~6.9M | 32% |

**The prune case, one session, timestamps from the log** (`in / cache_creation / cache_read / total`):

```
#306 05:12:59      32      517  745,871  746,420
#307 13:34:24       2  705,032   42,113  747,147   <- 8h idle: TTL, full re-write (expected)
#308 13:35:11      32    3,638  747,145  750,815
#309 13:35:36       2  618,703   47,638  666,343   <- context shrank 84k, everything after the shared prefix re-written
...
#432 16:42:35       2      306  844,913  845,221
#433 16:42:54       2  714,875   47,638  762,515   <- shrank 83k, re-written again
```

The binary confirms the mechanism: strings `microcompact`, `microcompact_boundary`, `[Old tool result content cleared]`, `snipTokensFreed`, `prefixTokens`, plus `<persisted-output>` for large results. Clearing old tool results *in place* changes bytes near the front of the history, so the KV prefix is valid only up to the first cleared block — in practice, only the system prompt survives.

At #307 the write was unavoidable. At #309, 60 seconds later, a second ~620k write bought 84k of freed context. If the prune had run at #307 — the cache was already cold — the second write would not exist. Across the four events: ~3.0M tokens written to free ~330k.

### 2.4 Resume

Two sessions resumed with `cache_read = 49,043` (or 48,208) and `cache_creation` = 219k–353k, gap ≈ 0. The shared prefix hit; the project layer did not. Something in the project part of the system prompt differs between the original session and the resumed one (date, hook output, git/branch state, memory index, tool list ordering — could not tell from the log). Because that block precedes the history, the entire history is re-written. The in-app setting text already warns that overriding the auto-compact window "may result in high token usage, especially when resuming long sessions" — this is the mechanism behind it.

### 2.5 What did *not* show up

- No duplicated parallel writes at session start (an earlier read of the logs suggested "the same 34k written 3×"; it was the per-content-block duplication above).
- No cache breaks caused by memory-file edits or CLAUDE.md edits mid-session in this sample.

## 3. Cost model

The pattern fits the "full history" regime in *Total Recall at What Cost?* (Bricks et al., arXiv 2608.11879, §5): per-turn cost ∝ history length × depth (their fitted exponents p ≈ q ≈ 1), so cumulative cost is quadratic in turns. Cache reads make each unit cheap, but with 320k average context and 3,200 calls the reads still dominate — and every cache break re-prices the whole history at write cost.

The levers, in order of measured size:

1. History length (drives 64% read + most of the 32% "normal" writes).
2. Cache-break scheduling (19% of total cost sits in 36 events; part of it is avoidable).
3. Prefix size (2% for CLAUDE.md — not worth touching).

## 4. What the literature says

All from arXiv papers of 2026 read in full; page refs are to the PDFs.

**TokenPilot: Cache-Efficient Context Management for LLM Agents** (Xu et al., arXiv 2606.17016, pp. 2–7). Cost model `K = α·hit + miss` with α the cached-token discount. Their central finding: text-level compressors (LLMLingua-2, SelectiveContext) *cost more than vanilla* in continuous multi-turn use because rewriting earlier context breaks the prefix — "pre-fill penalties and cache invalidations ultimately override any financial savings from text reduction" (p. 2). Their fix is **prompt-cache alignment**: keep evicted spans as stable placeholders (hit rate 38.7% → 79.2%) and **evict in batches** (B = 3 was optimal in their runs) instead of one item at a time. Section 2.3 above is the un-batched, un-aligned case.

**Inside the Scaffold: A Source-Code Taxonomy of Coding Agent Architectures** (Rombaut, arXiv 2604.03515, §4.3.2, pp. 21–23). Claude Code is excluded from the corpus ("compiled TypeScript bundles", p. 6) — so the logs above are the only outside view of its context management. Two relevant designs from the 13 open agents:
- **SWE-agent's `polling` parameter** on `LastNObservations`: truncation changes are applied only every k steps, "keeping the prefix stable across consecutive calls" — explicitly to preserve provider prompt caching (p. 23).
- **OpenCode's two-phase compaction**: first replace tool outputs older than the most recent 40,000 tokens with truncation markers (structure kept), only then LLM-summarize — with a cheaper model (p. 22).
- **Codex CLI** distinguishes pre-turn compaction (before a user turn, re-injects initial context cleanly) from mid-turn compaction (inside tool execution) (p. 22).

**Less Context, Better Agents** (Microsoft, arXiv 2606.10209, Tables 5, 7, 8). GPT-5 on Dynamics 365 via MCP, tool results 500–3k tokens. Keep the last N = 5 tool results verbatim plus a running summary of window W = 3: **−63% tokens and accuracy 71% → 91.6%** versus unbounded history (N = ∞). N = ∞ was the worst on both axes. Summarizing the *entire* history (W = −1, closest to `/compact`) kept 92% accuracy at +11% tokens — so full summaries do not hurt quality, they just cost more than a bounded window. Mechanism (Table 5): pruning removes stale-state errors (34 → 6) but triples premature termination (9 → 18); the summary brings that back (18 → 3). Caveat: with Sonnet 4.5 tokens fell 39% but wall-clock rose 6.2h → 11.3h, unexplained in the paper.

**Scroll / Context as an Environment** (ch. 2, pp. 2–5). Tool results live in a kernel variable; only what the agent `print`s enters the context; evicted spans stay addressable in an event log (`seq`, `expand(seq)`). Claude Code's `<persisted-output>` is the same idea for large results — the design is already there, the question is only *when* eviction runs relative to the cache.

**Total Recall at What Cost?** (arXiv 2608.11879, §5.2–5.4). Quadratic accumulation for full history; rolling window gives q ≈ 0.1. Also notes that a prefix cached at one provider does not hit on a fallback provider — same principle as the model switch in 2.3 (Fable → Opus re-wrote 615k).

**AI Engineering**, ch. "LLM Optimization", pp. 305–331: prefix-aware routing — a request that lands on a replica without the prefix re-computes it. Server-side, but the same asymmetry: one wrong placement costs a full prefix.

## 5. Suggestions

Ordered by (measured impact) / (implementation size). All are scheduling changes, not new subsystems.

1. **Cache-aligned compaction.** When the client can predict a cold request — last request > ~55 min ago, model switch, session resume, first call after `/clear`-less restart — run microcompact (and, if due, autocompact) *before* that request. The write is being paid anyway; the prune rides free. The binary already logs `prefixTokens` / `snipTokensFreed` per compaction, so the signal is at hand. (Note: `CLAUDE_CODE_COLD_COMPACT` looked like this feature by name, but in 2.1.266 it only sets `stripNonEssential` on the autocompact summary — a leaner summary, not cache-aware scheduling.) (TokenPilot §3; SWE-agent polling.)

2. **Batch the prune.** Four prunes of ~83k at 750–950k context cost ~3.0M write tokens; one prune of ~330k would have cost ~0.8M. When a snip is triggered, free a larger budget (or free down to a lower watermark) so the next trigger is far away. Equivalent to TokenPilot's batch eviction and SWE-agent's `polling`.

3. **Byte-stable project prefix on resume.** Whatever differs in the system prompt between a session and its resume (date line, hook output, git state, tool ordering) should sit *after* the stable block or in the first user turn, so `cache_read` on resume covers the history, not just the shared 49k. The setting text already warns about resume cost; this removes the cause rather than warning about it.

4. **Consider a bounded-history mode.** "Keep last N tool results verbatim + running summary" (Less Context, Table 7) beat both N = ∞ and full-history summary on cost, and matched or beat them on accuracy in that benchmark. Today's default (grow to the window, then summarize everything) is the most expensive point on their curve. Could start as an opt-in `autoCompact` mode; the microcompact machinery is most of the implementation.

5. **Expose cache health.** `/cost` or the status line could show per-turn `cache_read` vs `cache_creation` and a "cold" marker. Users cannot act on what they cannot see; the 8-hour idle → 705k re-write in 2.3 would have been a `/compact` before stepping away if the cost were visible.

6. **Document the jsonl duplication.** One line per content block, same `usage` on each. Anyone building cost tooling on the logs (several community projects do) is over-counting unless they dedup by `message.id`.

## 6. Caveats

- One user, one machine, 30 sessions, mostly long ones (1M context on). The *shares* will differ for short-session users; the *mechanisms* (TTL, prune, resume) will not.
- Claude Code's source is not readable; "microcompact" behaviour is inferred from usage deltas and string constants in `claude.exe`, not from code.
- Pricing multipliers are from public docs and may not match the subscription's internal accounting.
- The papers' benchmarks (D365 tools, SWE-bench-style agents, GPT-5 / Sonnet 4.5) are not Claude Code; the numbers transfer as directions, not magnitudes.

## Appendix — reproduce

```python
# dedup + per-call usage for one log
import json, sys
seen = set()
for l in open(sys.argv[1], encoding='utf-8'):
    d = json.loads(l)
    if d.get('type') != 'assistant': continue
    m = d['message']; u = m.get('usage')
    if not u: continue
    k = (m.get('id'), d.get('requestId'))
    if k in seen: continue
    seen.add(k)
    print(d['timestamp'][11:19], u.get('input_tokens'), u.get('cache_creation_input_tokens'), u.get('cache_read_input_tokens'), u.get('output_tokens'))
```

Full versions: [`tools/sessions.py`](../tools/sessions.py) (per-session totals, dedup) and [`tools/breaks.py`](../tools/breaks.py) (cache-break classification).
