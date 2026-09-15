# issues fetched 2026-09-15

| # | score | st | +1 | cmt | title |
|--|--|--|--|--|--|
| [89488](md/89488.md) | 98.0 | o | 0 | 0 | [FEATURE] Per-model prompt-cache TTL — extend promptCacheTtl to a per-model map |
| [45381](md/45381.md) | 97.3 | c | 163 | 13 | [BUG] Disabling telemetry also disables 1-hour prompt cache TTL |
| [84289](md/84289.md) | 95.2 | o | 1 | 3 | [DOCS] prompt-caching.md says subagents use the 5-minute TTL, but transcripts show 100% 1-hour cache |
| [84253](md/84253.md) | 81.6 | o | 0 | 2 | [BUG] Claude Code 2.1.218+ no longer requests 1h prompt-cache TTL — every 5+ min gap forces full cac |
| [34629](md/34629.md) | 79.3 | c | 44 | 25 | [BUG] Prompt cache regression in --print --resume since v2.1.69(?): cache_read never grows, ~20x cos |
| [62217](md/62217.md) | 79.1 | c | 0 | 3 | Support configurable prompt cache TTL for subagent launches |
| [46829](md/46829.md) | 78.6 | c | 342 | 56 | Cache TTL silently regressed from 1h to 5m around early March 2026, causing quota and cost inflation |
| [87966](md/87966.md) | 77.6 | o | 0 | 10 | [BUG] Prompt cache lookup fails intermittently mid-session — cache_read pinned to the stable-prefix  |
| [94177](md/94177.md) | 77.6 | o | 0 | 2 | Prompt-cache forensics from 30 real sessions: 68% of cache writes come from 36 events (TTL expiry, m |
| [63930](md/63930.md) | 77.1 | c | 7 | 12 | Prompt cache fully re-created after turns with many parallel tool calls (cache_read collapses to sys |
| [54006](md/54006.md) | 76.8 | c | 3 | 5 | [BUG] Agent team subagents do not honor 1-hour prompt cache TTL — main sessions show 100% 1h, every  |
| [14628](md/14628.md) | 75.5 | c | 4 | 5 | [BUG] Prompt Cache TTL Reduced from ~5 to ~3 Minutes Without Documentation (Mid-December 2025) |
| [82563](md/82563.md) | 74.6 | o | 0 | 2 | [BUG] Prompt Cache: Full Conversation Prefix Re-written 3 times Seconds Apart (Multiple Sessions & M |
| [74318](md/74318.md) | 74.1 | o | 5 | 5 | [FEATURE] Subagent prompt-cache strategy inflates prompt spend ~14% — 3 structural fixes (measured) |
| [88755](md/88755.md) | 72.9 | o | 0 | 6 | [BUG] Advisor is omitted from internal fork requests, so /compact re-bills the whole conversation as |
| [29966](md/29966.md) | 72.8 | o | 12 | 7 | Agent SDK subagents have prompt caching disabled by default (enablePromptCaching: false) |
| [83913](md/83913.md) | 72.1 | o | 4 | 8 | Prompt cache invalidated when PreToolUse/PostToolUse additionalContext changes during history rebuil |
| [89621](md/89621.md) | 71.0 | o | 0 | 0 | Prompt cache misses beyond ~16K prefix in long-running subagent with large multimodal context — full |
| [77306](md/77306.md) | 70.7 | o | 2 | 4 | [BUG] Session forks (--fork-session / /branch) forfeit the entire conversation prompt cache: session |
| [56307](md/56307.md) | 69.6 | c | 0 | 2 | [FEATURE] Adaptive cache-TTL heuristic — ~37% of 1h writes don't pay back over 5m |
| [64901](md/64901.md) | 69.1 | c | 0 | 3 | [BUG] Async sub-agent completion can rebuild warm prompt cache, quickly burning usage limits in long |
| [13997](md/13997.md) | 68.8 | c | 1 | 5 | The bug: BqA() in cli.js counts cache_creation_input_tokens and cache_read_input_tokens toward conte |
| [45756](md/45756.md) | 68.4 | o | 160 | 60 | [BUG] Pro Max 5x Quota Exhausted in 1.5 Hours Despite Moderate Usage |
| [70459](md/70459.md) | 68.3 | o | 3 | 7 | Auto-compaction: two compounding cost bugs — stale precompute keeps ~200k tokens verbatim, and that  |
| [93499](md/93499.md) | 68.1 | o | 1 | 1 | [FEATURE] Cache CLAUDE.md and rules across sessions: they are re-written to the prompt cache at ever |
| [51218](md/51218.md) | 68.0 | c | 1 | 6 | [BUG] Prompt cache expires during active session, causing massive token spikes on next prompt |
| [81967](md/81967.md) | 67.9 | o | 0 | 6 | [Bug] Prompt cache invalidation: tools array mutation and TTL downgrade during session |
| [60316](md/60316.md) | 66.9 | c | 7 | 2 | Expose `cache_control.ttl` (5m / 1h) as a user-configurable setting |
| [46917](md/46917.md) | 66.8 | o | 219 | 41 | CC v2.1.100+ inflates cache_creation by ~20K tokens vs v2.1.98 — same payload, server-side |
| [91706](md/91706.md) | 66.0 | o | 0 | 0 | [BUG] A persisting `cd` in a Bash tool call re-resolves project context and rewrites the system prom |
| [24147](md/24147.md) | 65.7 | o | 15 | 17 | Cache read tokens consume 99.93% of usage quota - architectural scaling issue with CLAUDE.md re-read |
| [92033](md/92033.md) | 64.7 | o | 2 | 4 | Mid-conversation tool/MCP list changes silently invalidate prompt cache, causing repeated full-price |
| [68140](md/68140.md) | 64.3 | c | 7 | 1 | [BUG] TodoWrite re-stamps a front-of-context block on every update, invalidating the entire prompt c |
| [47425](md/47425.md) | 64.2 | o | 10 | 1 | Feature request: intermediate prompt cache TTL tiers (15m, 30m) for interactive use |
| [27048](md/27048.md) | 63.8 | c | 0 | 12 | [BUG] Prompt Cache Invalidation on Session Resume: Tool-Use Content Not Cached, Plugin State Changes |
| [29876](md/29876.md) | 63.7 | c | 4 | 6 | Unexpected 2x token burn rate on MAX plan - possibly related to recent prompt caching changes |
| [77001](md/77001.md) | 63.7 | o | 0 | 5 | Disproportionate subscription usage burn in long sessions: cache TTL expiry re-writes + no usage att |
| [87215](md/87215.md) | 63.6 | o | 0 | 2 | [BUG] Waking a parked subagent re-caches its entire context: only the system prefix is served from c |
| [90584](md/90584.md) | 63.0 | o | 0 | 0 | MCP tool_reference scrub invalidates the prompt cache when servers are still `pending` on a fresh CL |
| [44724](md/44724.md) | 62.6 | c | 0 | 10 | Subagent cache miss on first SendMessage resume (cache_read=0) |
| [63962](md/63962.md) | 60.9 | c | 7 | 5 | [BUG] /effort change confirmation dialog warns about cache miss, but cache is preserved |
| [49038](md/49038.md) | 60.9 | c | 0 | 6 | Prompt cache miss on resume: Agent tool description enumerates sub-agents in non-deterministic order |
| [61984](md/61984.md) | 60.6 | c | 0 | 2 | Docs: `/effort` changes documented as "no effect on the cache" but empirically cause full/partial ca |
| [91705](md/91705.md) | 60.6 | c | 0 | 2 | [BUG] A pasted image is re-rendered as a file pointer on the next request: one full prompt-cache rew |
| [91514](md/91514.md) | 60.1 | o | 0 | 3 | [BUG] Warm prompt cache fully re-written (cache_read collapses to system+tools floor) seconds after  |
| [5904](md/5904.md) | 59.9 | c | 20 | 11 | [BUG] Local /cost doubles usage when parsing session JSONL (cache write & I/O tokens; ~2× total) |
| [90018](md/90018.md) | 59.8 | o | 3 | 2 | [BUG] totalTokensReminder causes repeatable prompt-cache floor in tool loops; off restores increment |
| [90009](md/90009.md) | 59.6 | o | 0 | 2 | [BUG] Forking from unprimed post-compact context re-bills the full shared prefix twice (fork AND par |
| [63981](md/63981.md) | 59.4 | c | 0 | 4 | Multi-lane Workflow agents re-create shared prompt cache per lane (no cross-sibling sharing), causin |
| [11008](md/11008.md) | 59.2 | o | 31 | 24 | [FEATURE] Expose token usage and cost data in hook inputs |
| [36243](md/36243.md) | 59.2 | c | 1 | 3 | [BUG] ENABLE_PROMPT_CACHING_1H_BEDROCK does not apply 1h TTL to subagent requests |
| [88412](md/88412.md) | 59.1 | c | 0 | 3 | [BUG] Waking an idle agent fork (`subagent_type: "fork"`) forfeits its inherited prompt cache on eve |
| [40652](md/40652.md) | 59.0 | c | 13 | 14 | CLI mutates historical tool results via cch= billing hash substitution, permanently breaking prompt  |
| [76058](md/76058.md) | 59.0 | o | 0 | 0 | [BUG] 1h prompt cache intermittently invalidated every ~11-12 min in active sessions, full conversat |
| [51764](md/51764.md) | 58.2 | c | 1 | 3 | `--continue`/`--resume` cache invalidation still reproduces on v2.1.116 — TTL-matched control shows  |
| [92938](md/92938.md) | 58.0 | o | 0 | 0 | [BUG] Prompt cache for resumed session history intermittently fails to hit on `resume`, independent  |
| [65636](md/65636.md) | 57.9 | c | 0 | 6 | [BUG] Oversized-image 400 error triggers a retry loop that invalidates prompt cache and inflates cos |
| [27786](md/27786.md) | 57.5 | c | 1 | 4 | Agent SDK: prompt cache invalidated every query() — random UUID in Bash tool description |
| [45188](md/45188.md) | 57.3 | c | 4 | 9 | System prompt size grew ~70K tokens between v2.1.89 and v2.1.96, making sessions unusable without fr |
| [77360](md/77360.md) | 57.1 | o | 0 | 3 | Browser automation in near-1M-token sessions silently burns extreme token volume (~43M cache-read to |
| [49139](md/49139.md) | 56.8 | c | 1 | 5 | [BUG] ENABLE_PROMPT_CACHING_1H is not working (API key user) |
| [42338](md/42338.md) | 56.8 | c | 1 | 11 | Session resume (--continue) invalidates entire prompt cache, causes massive rate limit consumption |
| [53065](md/53065.md) | 56.6 | o | 7 | 17 | advisor() tool inflates reported input tokens by forwarding full transcript, triggering premature au |
| [1347](md/1347.md) | 56.4 | c | 9 | 19 | [BUG] Prompt Caching Works on Claude 3.7 But Not On Claude 4 Family (AWS Bedrock) |
| [34805](md/34805.md) | 56.2 | c | 1 | 3 | Auto-compaction triggers at 41% actual context usage on 1M Opus 4.6 sessions (token estimation over- |
| [89418](md/89418.md) | 56.0 | o | 0 | 0 | [BUG] Request-Size-Driven Image Pruning Repeatedly Invalidates Prompt Cache and Amplifies Cache Writ |
| [48240](md/48240.md) | 55.6 | c | 0 | 2 | Feature request: Let users disable prompt caching for prompt hooks, especially Stop hooks |
| [48137](md/48137.md) | 55.2 | c | 1 | 3 | Prompt cache TTL too short for neurodivergent users and complex workflows |
| [42309](md/42309.md) | 55.1 | c | 0 | 7 | [DOCS] `--resume` prompt cache behavior with deferred tools, MCP servers, and custom agents is undoc |
| [18726](md/18726.md) | 55.1 | c | 0 | 3 | [DOCS] Clarify "Worst-Case" cost estimation in Token Counting API regarding Prompt Caching |
| [93295](md/93295.md) | 55.0 | o | 0 | 0 | [BUG] `DISABLE_PROMPT_CACHING_HAIKU` is silently ignored when Haiku is the main model — undocumented |
| [91707](md/91707.md) | 55.0 | o | 0 | 1 | [BUG] Turn-boundary prompt-cache misses on Fable 5.1 / Claude 5: 7% → 29% between 2.1.224 and 2.1.25 |
| [80604](md/80604.md) | 55.0 | o | 0 | 1 | Agent Teams teammate delivery intermittently triggers full conversation cache rewrite (~400-513k cac |
| [44045](md/44045.md) | 54.6 | c | 0 | 20 | [BUG] Prompt cache partial miss on every --resume turn — skill_listing block missing from messages[0 |
| [56023](md/56023.md) | 54.5 | c | 4 | 2 | [FEATURE] Cacheable static prefix for Agent-tool prompts (cross-spawn cache hits for orchestrated su |
| [22417](md/22417.md) | 54.0 | c | 1 | 6 | [FEATURE] Reduce unexpected cache write costs on Bedrock |
| [90363](md/90363.md) | 54.0 | o | 0 | 0 | [BUG] "an image in the conversation could not be processed and was removed" is NOT removed from the  |
| [58953](md/58953.md) | 53.9 | c | 2 | 2 | [Perf/Cost] Tool catalog (~24k tokens) sent uncached on every API request — cache_control breakpoint |
| [66005](md/66005.md) | 53.7 | o | 2 | 9 | [BUG] `--resume` drops the session's `--effort` level, invalidating the prompt cache |
| [59650](md/59650.md) | 53.6 | c | 0 | 2 | Deferred MCP tool schemas inflate cache reads and per-turn token counts unnecessarily |
| [59872](md/59872.md) | 53.5 | c | 0 | 9 | Opus 4.6 cache_read tokens counted at full rate despite cache hits on Max 20x |
| [40459](md/40459.md) | 53.2 | c | 3 | 14 | v2.1.84+: subagents lose CLAUDE.md context (omitClaudeMd:true), reduced instruction adherence with p |
| [80821](md/80821.md) | 53.0 | c | 0 | 1 | [Bug] Excessive cache creation tokens with low cache read ratio causing high usage consumption |
| [84738](md/84738.md) | 52.5 | o | 4 | 2 | Advisor turns roll up usage summed across iterations, doubling apparent context; auto-compact fires  |
| [45958](md/45958.md) | 52.2 | c | 2 | 6 | [BUG] [AGENT_TEAMS] Parallel Agent dispatch: 90min stall silently burns ~15M cache_read tokens, rese |
| [69468](md/69468.md) | 52.1 | c | 0 | 3 | Empirical log audit of 9,911 sessions: Claude Code prompt caching bottlenecks & optimization recomme |
| [94417](md/94417.md) | 52.0 | o | 0 | 0 | CLAUDE.md / auto-memory block is never shared across sessions: it sits in messages[0] after the syst |
| [81077](md/81077.md) | 51.5 | c | 1 | 4 | [Harness] PostToolUse additionalContext re-serialized between turns, invalidating prompt cache |
| [28167](md/28167.md) | 51.2 | c | 4 | 4 | Context usage percentage only counts input tokens, causing misleading 'Context limit reached' at ~20 |
| [90953](md/90953.md) | 51.1 | o | 1 | 0 | [FEATURE] Expose a "why did this cache miss happen" diagnostic |
| [92444](md/92444.md) | 51.0 | o | 0 | 0 | [BUG] /effort mid-session invalidates the prompt cache on Sonnet 5 and Opus 5 (full rewrite on Opus) |
| [86579](md/86579.md) | 51.0 | c | 0 | 1 | [Bug] iOS Simulator screenshots trigger persistent messages_changed cache misses and full 1h message |
| [49585](md/49585.md) | 50.6 | c | 0 | 20 | [BUG] Per-turn smoosh pipeline folds dynamic <system-reminder> text into tool_result.content, breaki |
| [63282](md/63282.md) | 50.1 | c | 0 | 3 | [BUG] Opus 4.7 cache hit rate collapse after May 27 incident — Messages 1.1k→88.9k in 9 minutes, $63 |
| [53132](md/53132.md) | 50.1 | c | 0 | 3 | [BUG] ToolSearch unlock invalidates prompt-cache prefix mid-session |
| [27787](md/27787.md) | 50.1 | c | 0 | 3 | Agent SDK: WebFetch tool description flickers between query() calls, breaking prompt cache |
| [85326](md/85326.md) | 50.0 | o | 0 | 0 | Prompt cache dropped every ~40s in large sessions: full ~950k context re-written at 2x cost (v2.1.22 |
| [48644](md/48644.md) | 49.9 | c | 2 | 2 | [BUG] Hidden `isMeta` system-reminder causes 200k+ cache_creation burst mid-session (Opus 4.6) |
| [41788](md/41788.md) | 49.6 | o | 86 | 60 | Max 20 plan: rate limit 100% exhausted within ~70 minutes after reset (never happened before v2.1.89 |
| [91151](md/91151.md) | 49.6 | o | 0 | 2 | [BUG] Prompt cache collapses to the system+tools floor on every resumed turn once the conversation e |
| [48734](md/48734.md) | 49.6 | c | 2 | 8 | [BUG] Historical user-message content drift invalidates prompt cache prefix (trailing \n on </system |
| [38350](md/38350.md) | 49.5 | o | 42 | 63 | [BUG] Abnormal / inflated rate limit / session usage |
| [39803](md/39803.md) | 49.5 | c | 1 | 4 | [BUG] Anomalous cache read token consumption with agent-based workflows (19.5M tokens for a single f |
| [43657](md/43657.md) | 49.1 | c | 9 | 15 | [BUG] Resume/continue cache invalidation |
| [94197](md/94197.md) | 49.0 | o | 0 | 1 | [FEATURE] Every compaction re-writes ~97k unchanged tokens to cache because the summary is assembled |
| [48808](md/48808.md) | 48.8 | c | 1 | 5 | [BUG] 2x - 3x increase in output tokens starting with version 2.1.96 and increasing in 2.1.101 |
| [86075](md/86075.md) | 48.7 | o | 1 | 2 | [BUG] Image tool results can't be persisted, so budget eviction replaces them with a sentinel mid-hi |
| [78720](md/78720.md) | 48.6 | o | 0 | 2 | [BUG] -p --resume from a git repo: any `git status` change between turns invalidates the entire prom |
| [63015](md/63015.md) | 48.5 | o | 22 | 29 | [Bug] Auto-compact never triggers despite statusline reporting "100% context used" (v2.1.153, Max su |
| [49302](md/49302.md) | 48.5 | c | 5 | 7 | [Bug] Opus 4.7 metering: cache_read_input_tokens consuming 5-hour bucket at input-token rate (Max $1 |
| [66115](md/66115.md) | 48.2 | o | 16 | 5 | Feature request: auto-compact on idle timeout to prevent cache expiry cost |
| [55445](md/55445.md) | 48.1 | c | 0 | 3 | Cache_creation tokens per turn doubled (2.18x) after migrating from VS Code extension to desktop app |
| [46422](md/46422.md) | 48.1 | c | 0 | 3 | [BUG] Token estimation vs API-reported tokens diverge significantly for cached context |
| [91971](md/91971.md) | 47.7 | o | 0 | 5 | Prompt cache never hits across chained -p --resume calls, even at minimum config |
| [70158](md/70158.md) | 47.7 | c | 1 | 2 | [FEATURE] Inject skill content into cached system prompt instead of message history (lower token cos |
| [48896](md/48896.md) | 47.7 | c | 0 | 5 | [BUG] Excessive token consumption — ~2000 tokens per   simple query with prompt cache enabled |
| [21644](md/21644.md) | 47.4 | o | 15 | 1 | [BUG] prompt-caching-scope-2026-01-05 beta header sent even when enablePromptCaching and useAnthropi |
| [52979](md/52979.md) | 47.3 | c | 5 | 13 | [BUG] Excessive token usage (~20k–30k tokens) for trivial prompts in Claude Code CLI |
| [54770](md/54770.md) | 47.1 | c | 5 | 5 | [BUG] Rapid quota consumption in Claude Code with Opus 4.7 1M context — minutes-scale 90%+ burn from |
| [42647](md/42647.md) | 47.1 | c | 4 | 8 | [BUG] High Token Burn Due to Redundant Context Resubmission & Compaction Loops |
| [68900](md/68900.md) | 47.1 | c | 0 | 3 | Billing-header nonce (`cch`) in system prompt breaks prompt caching on third-party providers |
| [93848](md/93848.md) | 47.0 | o | 0 | 0 | [BUG] Embedded CLAUDE.md intermittently reaches the API with one multibyte character replaced by thr |
| [94400](md/94400.md) | 47.0 | o | 0 | 0 | [BUG] Resumed session drops a tool from the parent's initial tools array (EndConversation), so its f |
| [84011](md/84011.md) | 47.0 | o | 0 | 1 | PreToolUse hook additionalContext loses trailing newline on history rebuild, breaking prompt cache a |
| [76606](md/76606.md) | 46.9 | o | 0 | 6 | [BUG] Prompt cache invalidated by rewrites of messages in long sessions |
| [49588](md/49588.md) | 46.9 | c | 2 | 2 | [FEATURE] Expose session token usage to MCP servers and hooks for cost attribution |
| [47261](md/47261.md) | 46.6 | c | 0 | 2 | [Bug] Resume sessions write ephemeral_5m cache instead of ephemeral_1h, wasting 70-140k tokens per r |
| [59975](md/59975.md) | 46.4 | c | 0 | 4 | [FEATURE] Expose runtime metadata (token usage, context %, compaction status) to the model inside th |
| [42542](md/42542.md) | 46.3 | o | 11 | 25 | [BUG] Silent context degradation — tool results cleared without notification on 1M context sessions  |
| [33978](md/33978.md) | 46.1 | o | 11 | 21 | [FEATURE] Built-in Usage Analytics Command (claude usage) — Consolidates 10+ Open Issues |
| [78165](md/78165.md) | 46.1 | o | 1 | 1 | Feature: model-initiated /compact at task boundaries (agentic compaction instead of threshold-only) |
| [16524](md/16524.md) | 46.1 | c | 0 | 3 | Feature Request: Include total context usage in statusline JSON |
| [90716](md/90716.md) | 46.0 | o | 0 | 1 | [BUG]  Image eviction in long sessions mutates the conversation prefix, forcing a full context re-ca |
| [83756](md/83756.md) | 46.0 | o | 0 | 0 | [BUG] Large MCP `ToolSearch` batches invalidate the whole conversation cache, contradicting the docu |
| [90144](md/90144.md) | 46.0 | o | 0 | 1 | [BUG] Opening a session with a large slash command makes the second request discard the entire promp |
| [74075](md/74075.md) | 45.4 | c | 0 | 4 | Expose extended (1h) prompt-cache TTL for interactive sessions |
| [14963](md/14963.md) | 45.4 | c | 0 | 4 | Prompt Caching Inefficiency - Dynamic Variables Placed Before Static Tool Definitions |
| [34332](md/34332.md) | 45.3 | o | 10 | 7 | Opus 4.6 (1M context): autocompact triggers at ~76K tokens — 92% of context window wasted |
| [72913](md/72913.md) | 45.2 | c | 1 | 3 | [Bug][cyber] False cyber block on cache-fix-warmer maintenance cron (req_011CcbvVXnTau2SguZK9QyDd) |
| [92090](md/92090.md) | 45.1 | o | 1 | 1 | [BUG] Fable 5.1 subagents re-cache their entire context (200-430K tokens) turn after turn: the 5-min |
| [87137](md/87137.md) | 45.1 | o | 0 | 3 | `Bash` tool description embeds the per-session URL, so every `/resume` invalidates the whole prompt  |
| [88444](md/88444.md) | 44.7 | o | 0 | 5 | [BUG] Resuming a fork forfeits its prompt cache: deterministic miss after any tool loop, fork 5m vs  |
| [61334](md/61334.md) | 44.7 | c | 0 | 5 | [BUG] Compaction threshold regression in 2.1.144+: MCP tool definitions over-counted, auto-compact f |
| [40524](md/40524.md) | 44.5 | c | 223 | 124 | [BUG] Conversation history invalidated on subsequent turns |
| [77266](md/77266.md) | 44.2 | c | 3 | 1 | [FEATURE] |
| [10067](md/10067.md) | 44.2 | c | 3 | 3 | [FEATURE] Pre-built/compiled skills: Why they don't exist and what could be |
| [47045](md/47045.md) | 44.2 | c | 2 | 6 | SubagentStop hook payload should include token usage data |
| [67497](md/67497.md) | 44.1 | c | 1 | 1 | [BUG] v2.1.148: --resume cache invalidation — system-block scatter still present (refile of #43657 w |
| [40319](md/40319.md) | 44.1 | c | 2 | 12 | [BUG] Session resume loads zero conversation history — silently drops all context |
| [92238](md/92238.md) | 44.0 | o | 0 | 0 | [bug] [/cost] Current session 101% used |
| [51301](md/51301.md) | 43.7 | c | 2 | 4 | [Bug] Prompt cache invalidation causing excessive token consumption on minor edits |
| [66144](md/66144.md) | 43.7 | o | 25 | 13 | [BUG] Auto compact does not trigger at 100% context window and Claude Code stops itself on cli |
| [58515](md/58515.md) | 43.6 | c | 0 | 2 | Status check: cache TTL remediation commitments from #46829 - 30-day update |
| [81620](md/81620.md) | 43.5 | c | 4 | 5 | [BUG] `advisor` tool doubles the reported context size, firing auto-compact at ~50% of the real wind |
| [42249](md/42249.md) | 43.4 | o | 17 | 45 | [BUG] Extreme token consumption — quota depleted in minutes with normal usage |
| [15512](md/15512.md) | 43.4 | c | 2 | 3 | [Bug] Statusline JSON token counts don't match /context - possible calculation error |
| [6616](md/6616.md) | 43.3 | o | 13 | 18 | Context low warning and /compact failure despite having 86% free context space |
| [79665](md/79665.md) | 43.1 | o | 1 | 1 | [Bug] Auto-compact "context running low" warning fires at ~177k tokens in 1M-context ([1m]) sessions |
| [48082](md/48082.md) | 43.1 | c | 0 | 3 | [DOCS] Prompt caching TTL env var docs omit generic 1-hour and forced 5-minute controls |
| [91712](md/91712.md) | 43.0 | c | 12 | 8 | Let the Code tab's usage ring report session context, not only the 5-hour window |
| [76959](md/76959.md) | 43.0 | c | 0 | 1 | SendMessage to a completed subagent doesn't reuse the previous prompt prefix (cache miss on every re |
| [84457](md/84457.md) | 43.0 | o | 0 | 0 | [FEATURE] Don't charge the usage cap for context re-sent after a cap-interrupted session |
| [18456](md/18456.md) | 42.9 | c | 162 | 21 | [FEATURE] VSCode Extension: Display context usage percentage in UI |
| [18944](md/18944.md) | 42.8 | c | 3 | 5 | [BUG] Statusline API used_percentage significantly underreports context usage |
| [36014](md/36014.md) | 42.5 | c | 5 | 7 | [BUG] Autocompact triggers at 17% on 1M context model (effectiveWindow likely capped at 200k) |
| [39733](md/39733.md) | 42.4 | c | 0 | 4 | [BUG] result.modelUsage reports cumulative session totals, not per-turn deltas — breaks usage tracki |
| [14258](md/14258.md) | 42.3 | c | 48 | 21 | [FEATURE] PostCompact Hook Event and Compaction Content Control |
| [81234](md/81234.md) | 42.2 | c | 2 | 6 | [Bug] Max 20x weekly quota drained 53% in 2 days; transcript accounting shows those days were <half  |
| [92201](md/92201.md) | 42.0 | o | 0 | 1 | [Bug] Rate limit consumption disproportionate to measured token usage for opus-5-1m with prompt cach |
| [54563](md/54563.md) | 41.8 | c | 1 | 5 | [Bug] Prompt cache unexpectedly collapses mid-session on Opus 4.x |
| [30103](md/30103.md) | 41.6 | c | 3 | 4 | System scaffold tokens (tools/prompt) should use global cache and not be billed as user input |
| [54750](md/54750.md) | 41.3 | o | 12 | 20 | Bug: Claude Code current session limit reaches 100% despite low visible local session usage |
| [13783](md/13783.md) | 41.3 | c | 42 | 14 | [BUG] Statusline context_window JSON contains cumulative tokens instead of current context usage |
| [68147](md/68147.md) | 41.3 | c | 7 | 3 | Subagent model override silently dropped after a continuation boundary (SendMessage follow-up / post |
| [52519](md/52519.md) | 41.2 | c | 1 | 3 | Subscriber usage impact of 2.1.117 Opus 4.7 auto-compact threshold change not documented |
| [23751](md/23751.md) | 41.1 | c | 13 | 15 | Compaction fails with 'Conversation too long' at 48% context usage (Opus 4.6) |
| [78660](md/78660.md) | 41.1 | o | 0 | 3 | [BUG] task_reminder nudge fired mid-tool-loop rewrites cached history (near-total rebuild per firing |
| [65917](md/65917.md) | 41.1 | c | 0 | 3 | Transient MCP server disconnect evicts its tools from the front `tools` array → full prompt-cache pr |
| [89327](md/89327.md) | 41.1 | o | 1 | 0 | [BUG] Clean boot sends skill catalog in both Skill tool schema and skill_listing message |
| [22625](md/22625.md) | 41.0 | c | 9 | 3 | [FEATURE] Per-Subagent Token Usage Tracking |
| [87646](md/87646.md) | 41.0 | o | 0 | 1 | Usage: 91% of a Max subscriber's spend is context re-reading, with no in-product signal (25% of week |
| [83272](md/83272.md) | 41.0 | c | 0 | 1 | [Bug] Anthropic API fallback from claude-fable-5 to claude-opus-5 silently discards prompt cache |
| [44779](md/44779.md) | 41.0 | c | 1 | 6 | [BUG] No visibility into session token cost — 1M context window makes existing warnings useless |
| [34556](md/34556.md) | 40.9 | c | 6 | 113 | Feature Request: Persistent Memory Across Context Compactions (59 compactions, built our own) |
| [88211](md/88211.md) | 40.9 | o | 2 | 2 | [BUG] Default totalTokensReminder (padded-countdown) shows a number unrelated to context usage — mod |
| [16988](md/16988.md) | 40.8 | c | 5 | 4 | Feature Request: Add context usage percentage to hooks and enable automatic /compact execution |
| [74473](md/74473.md) | 40.6 | c | 9 | 2 | Bundled claude-api skill injects entire 570KB SKILL.md (~210k tokens) into context on load |
| [43566](md/43566.md) | 40.6 | c | 3 | 4 | [BUG] Cache TTL silently downgrades from 1h to 5m when Extra Usage is active |
| [17959](md/17959.md) | 40.5 | o | 18 | 5 | context_window.used_percentage doesn't match internal context warning calculation |
| [35794](md/35794.md) | 40.4 | c | 0 | 4 | [FEATURE] Community proxy that adds persistent memory, smart compaction, cache keepalive and token o |
| [21567](md/21567.md) | 40.3 | o | 15 | 13 | Terminal renderer CPU spin: 100% CPU with 625K writes/0 blits on large session |
| [18386](md/18386.md) | 40.3 | c | 5 | 6 | Token counting ~2x inflated in 2.1.7 vs 2.1.2 |
| [47098](md/47098.md) | 40.2 | c | 3 | 14 | [BUG] new sessions will **never** hit a (full)cache |
| [42749](md/42749.md) | 40.2 | c | 1 | 3 | Resuming sessions from v2.1.89 in v2.1.90 causes excessive token usage (no prompt caching) |
| [74912](md/74912.md) | 40.2 | o | 4 | 4 | [BUG] Local-scoped plugin fails to load on Windows with `plugin-cache-miss` due to case-sensitive `p |
| [83512](md/83512.md) | 39.9 | o | 4 | 1 | statusLine always reports the main session, even when a subagent or teammate transcript is focused |
| [54934](md/54934.md) | 39.7 | c | 1 | 2 | [BUG] Thinking stalls exceeding conversation cache TTL |
| [54716](md/54716.md) | 39.6 | c | 11 | 7 | Allow opt-out of built-in deferred tools via settings to reduce baseline context |
| [7111](md/7111.md) | 39.6 | c | 23 | 14 | Feature Request: Restore Time & Token Indicators + Add Context Usage Display |
| [6223](md/6223.md) | 39.4 | c | 4 | 10 | [BUG] SDK (TypeScript at least) fails to invoke hooks |
| [18159](md/18159.md) | 39.4 | o | 15 | 14 | [Bug] Context limit reached with 32k tokens free space and auto-compact disabled |
| [63197](md/63197.md) | 39.4 | c | 1 | 8 | [BUG] Compaction fails with "context window limit" error even when context usage is low (e.g., 20%)  |
| [27665](md/27665.md) | 39.3 | o | 22 | 12 | [FEATURE] Intelligent Model Routing — Claude Code routes 93.8% of Max subscriber tokens to Opus with |
| [82863](md/82863.md) | 39.3 | o | 2 | 1 | [Bug] Auto-compact consumes double-counted usage: preTokens=1,364,156 on a 1M window while real cont |
| [10447](md/10447.md) | 39.2 | o | 55 | 15 | Feature Request: CLI Commands for MCP Server Enable/Disable (Hook Automation Support) |
| [89659](md/89659.md) | 39.1 | o | 1 | 0 | [BUG] Prompt suggestions send a second full-context model call per turn, ~doubling token usage |
| [93572](md/93572.md) | 39.0 | o | 0 | 0 | [FEATURE] Persistent project-scoped prompt cache, independent of thread/session lifetime |
| [19724](md/19724.md) | 39.0 | c | 1 | 6 | [BUG] claude code "current_usage" is broken for statusline |
| [8861](md/8861.md) | 38.8 | c | 12 | 7 | [FEATURE] Add token usage details to status line API |
| [16157](md/16157.md) | 38.7 | o | 725 | 1494 | [BUG] Instantly hitting usage limits with Max subscription |
| [6915](md/6915.md) | 38.6 | c | 378 | 89 | Allow MCP tools to be available only to subagent |
| [33603](md/33603.md) | 38.6 | o | 14 | 19 | CLAUDE.md hard rules and persistent memory instructions consistently ignored — violations escalate w |
| [93799](md/93799.md) | 38.6 | o | 0 | 2 | Hitting the weekly limit cost me a second subscription - session cost is invisible and the handoff i |
| [64598](md/64598.md) | 38.4 | c | 0 | 4 | [BUG] Read tool serves cached payload after failed Write, masking on-disk corruption (no cache inval |
| [2511](md/2511.md) | 38.3 | o | 639 | 50 | Feature request: Connect Claude code to Claude projects  |
| [87487](md/87487.md) | 38.2 | o | 3 | 1 | [FEATURE] Option to suppress the daily currentDate injection from the system prompt (prompt-cache fr |
| [69627](md/69627.md) | 38.2 | c | 1 | 3 | [FEATURE] clear_context_uses: cache-aware eviction of used context (skills / files / memories / tool |
| [65796](md/65796.md) | 38.2 | o | 0 | 15 | Workflow (multi-agent) resume restarts from the beginning after auto-compaction — silently re-runs c |
| [50204](md/50204.md) | 38.2 | c | 1 | 3 | [Bug] Auto-compact triggers prematurely with extended context models |
| [91110](md/91110.md) | 38.1 | o | 1 | 0 | [FEATURE] Expose the advisor tool's `caching` parameter in Claude Code |
| [25604](md/25604.md) | 38.1 | c | 3 | 6 | [Bug] Context limit reached at 21% usage after 11-minute extended thinking — /compact also fails |
| [6354](md/6354.md) | 37.9 | o | 30 | 21 | [BUG] Claude forgets everything in CLAUDE.md after compaction |
| [14111](md/14111.md) | 37.8 | c | 17 | 15 | [Bug] /compact and auto-compact fail with 'Tool names must be unique' when MCP servers are configure |
| [71301](md/71301.md) | 37.7 | c | 1 | 2 | [BUG] /context over-counts memory files and custom agents in 2.1.191; 2.1.179 reports sane estimates |
| [52176](md/52176.md) | 37.6 | c | 0 | 2 | InstructionsLoaded hook fires 3x per file per compact event (causes 3x context reload waste) |
| [27293](md/27293.md) | 37.4 | c | 5 | 14 | Feature request: lossless context cleanup before auto-compaction |
| [6235](md/6235.md) | 37.4 | c | 6626 | 394 | Feature Request: Support AGENTS.md. |
| [57699](md/57699.md) | 37.2 | c | 1 | 15 | Weekly limit depletes disproportionately to 5h-session limit on Max 20x — quantified telemetry shows |
| [12288](md/12288.md) | 37.2 | c | 56 | 7 | [BUG] ExitPlanMode doesn't return the plan as a tool result in v2.0.51 |
| [15815](md/15815.md) | 37.2 | c | 1 | 7 | [BUG] --agent Flag Not Working for Non Interactive (Affects SDK) |
| [40180](md/40180.md) | 37.2 | c | 1 | 3 | [FEATURE] Queryable context usage + selective context purge |
| [58618](md/58618.md) | 37.2 | c | 1 | 3 | [FEATURE] System prompt consumes user context window — should be separated |
| [38335](md/38335.md) | 37.0 | o | 545 | 853 | [BUG] Claude Max plan session limits exhausted abnormally fast since March 23, 2026 (CLI usage) |
| [91865](md/91865.md) | 37.0 | o | 0 | 0 | [BUG] |
| [82229](md/82229.md) | 37.0 | c | 0 | 1 | [Bug] Per-session console URL in the Bash tool description defeats cross-session prompt-cache reuse |
| [18314](md/18314.md) | 37.0 | c | 12 | 8 | [BUG] Auto compact off, but asking me to compact before 100% context usage |
| [90756](md/90756.md) | 37.0 | o | 0 | 1 | Desktop: Expose the auto-compact window in the usage ring that already shows context usage |
| [53199](md/53199.md) | 36.9 | c | 3 | 11 | [Bug] Auto-compact triggers far below 1M window on Opus 4.7 [1M] — severe token burn regression on M |
| [42796](md/42796.md) | 36.8 | c | 3286 | 583 | [MODEL] Claude Code is unusable for complex engineering tasks with the Feb updates |
| [38029](md/38029.md) | 36.8 | o | 39 | 23 | [BUG] Abnormal Usage Consumption on Claude Code Session Resume — Possible Bug |
| [34650](md/34650.md) | 36.8 | c | 25 | 14 | Add --max-context flag to cap context window usage |
| [40567](md/40567.md) | 36.7 | c | 1 | 2 | [FEATURE] Token cache guard |
| [17457](md/17457.md) | 36.7 | c | 2 | 9 | [BUG] Multiple duplicate warmup agents spawning causes idle token consumption |
| [16944](md/16944.md) | 36.6 | c | 0 | 2 | [DOCS] Document subagent auto-compaction behavior (compactMetadata and preTokens) |
| [81116](md/81116.md) | 36.5 | c | 0 | 9 | [BUG] Session usage shows "100% used" with $0.0000 cost and 0 tokens consumed |
| [62381](md/62381.md) | 36.4 | c | 2 | 3 | [DOCS] Document server-side system prompt experiments and their opt-out controls |
| [93490](md/93490.md) | 36.4 | o | 0 | 4 | [BUG] --resume never hits the prompt cache past the static prefix on Fable 5.1 (opus hits): session- |
| [56293](md/56293.md) | 36.4 | c | 0 | 4 | v2.1.128 caching regression in parallel-team workloads (10x token cost increase) |
| [77834](md/77834.md) | 36.4 | c | 0 | 4 | [BUG] Agent fan-out pays ~47K uncached startup tokens per small task, causing multi-million-token us |
| [45596](md/45596.md) | 36.3 | o | 2090 | 268 | Bring Back Buddy — A Consolidated Plea from the Community |
| [15404](md/15404.md) | 36.3 | c | 4 | 9 | Feature Request: Statusline should show total context usage (matching /context) |
| [30920](md/30920.md) | 36.2 | c | 3 | 3 | [BUG] API Error: MCP tools cannot have both defer_loading=true and cache_control set |
| [28927](md/28927.md) | 36.2 | o | 19 | 16 | [BUG] Silent billing change in v2.1.51: 1M context moved to extra-usage-only without notice — JSONL  |
| [41346](md/41346.md) | 36.2 | c | 1 | 7 | Extended thinking generates duplicate .jsonl log entries with identical input tokens, causing ~2-3x  |
| [42679](md/42679.md) | 36.2 | c | 1 | 3 | [FEATURE] Proactive token cost transparency & anomaly detection across all surfaces |
| [49753](md/49753.md) | 36.1 | c | 0 | 3 | Race between initialize control_request and MCP refresh causes tools to drop from first request |
| [76372](md/76372.md) | 36.1 | o | 1 | 1 | Desktop: ~3.9k tokens of built-in MCP tool schemas load non-deferred with no opt-out; built-in serve |
| [87855](md/87855.md) | 36.1 | o | 1 | 0 | [BUG] claude-sonnet-5 reported cost inflated exactly 1.5x — CLI pricing table uses $3/$15 instead of |
| [43989](md/43989.md) | 36.1 | c | 7 | 12 | v2.1.92 regression: autocompact threshold reduced to 400k on Opus 4.6 (1M context) |
| [17428](md/17428.md) | 36.0 | o | 116 | 44 | [Feature Request] Enhanced /compact with file-backed summaries and selective restoration |
| [92524](md/92524.md) | 36.0 | o | 0 | 0 | Per-session scratchpad UUID in the system prompt is the only cross-session prompt diff, invalidating |
| [78410](md/78410.md) | 36.0 | c | 0 | 1 | [DOCS] Prompt-caching docs do not explain mid-conversation system-block caching through gateways |
| [40584](md/40584.md) | 36.0 | c | 5 | 10 | [BUG] Client-side rate limiter blocks requests with zero API calls when conversation transcript is l |
| [49320](md/49320.md) | 35.9 | c | 6 | 3 | Feature request: include thinking_tokens in API usage response |
| [37342](md/37342.md) | 35.9 | o | 30 | 21 | [FEATURE] Support slash commands (/clear, /compact) from Channels (Telegram/Discord) |
| [56075](md/56075.md) | 35.8 | c | 5 | 9 | [BUG] Single README.md edit burns entire 5-hour Max 5x window in 9m 39s (Opus 4.7 1M, resumed sessio |
| [24016](md/24016.md) | 35.8 | c | 3 | 5 | Sessions spanning 5-hour rate-limit windows cause inflated usage attribution at window start |
| [68619](md/68619.md) | 35.7 | o | 22 | 33 | [CRITICAL] Subagent spawning and subagent pattern bugs trigger infinite recursion, infinite token us |
| [6805](md/6805.md) | 35.7 | c | 2 | 4 | [BUG] Token Usage Statistics Duplicated in stream-json Mode Causing Massive Cost Inflation |
| [5477](md/5477.md) | 35.7 | c | 2 | 4 | Feature Request: Enhanced Status Line with Context Information Integration |
| [83731](md/83731.md) | 35.7 | o | 1 | 2 | [MODEL] Opus 5 (1M) reports itself "out of context" at 28-50% usage and stops working; Opus 4.8 does |
| [19892](md/19892.md) | 35.6 | c | 3 | 4 | [Bug] Subagent outputs include verbose API metadata causing session slowdown |
| [14554](md/14554.md) | 35.6 | c | 26 | 11 | [BUG] Chat output content broken/missing/incomplete |
| [67746](md/67746.md) | 35.6 | c | 0 | 2 | [DOCS] [VS Code] Account & usage dialog `/usage` now shows per-skill/agent/plugin/MCP cache and long |
| [37793](md/37793.md) | 35.5 | o | 26 | 21 | Subagents fail with 'prompt is too long' when user has many MCP servers (tool definitions exceed 200 |
| [67847](md/67847.md) | 35.5 | o | 1 | 9 | Opus 4.8 fabricates entire tool executions inside extended thinking — no tool_use emitted, model bel |
| [63896](md/63896.md) | 35.5 | o | 26 | 41 | [BUG] Error: Error during compaction: API Error: Usage credits required for 1M context · turn on usa |
| [38357](md/38357.md) | 35.4 | c | 4 | 10 | [BUG] Max 20x: Usage meter climbing abnormally fast since ~March 23 — 1-2% per simple message exchan |
| [48236](md/48236.md) | 35.4 | c | 0 | 4 | [BUG] uncacheable system prompt caused by `Primary working directory:` in git worktree |
| [80305](md/80305.md) | 35.3 | o | 5 | 6 | [Bug] Task tools gated OFF in real-TTY CLI; CLAUDE_CODE_ENABLE_TASKS env var ineffective |
| [47107](md/47107.md) | 35.2 | c | 3 | 3 | [BUG] uncachable system prompt caused by includeGitInstructions / CLAUDE_CODE_DISABLE_GIT_INSTRUCTIO |
| [91836](md/91836.md) | 35.1 | o | 1 | 0 | Opt-in: compact the conversation at the end of a goal while the session is still cached |
| [57953](md/57953.md) | 35.1 | c | 0 | 3 | Expose /context per-category breakdown to status line scripts |
| [85954](md/85954.md) | 35.0 | c | 0 | 1 | Agent tool description flips to its subagent variant in the main conversation while in-process teamm |
| [14058](md/14058.md) | 35.0 | c | 15 | 5 | [Feature Request] Include actual context window usage in statusline JSON |
| [94346](md/94346.md) | 35.0 | o | 0 | 0 | [BUG] /context subtracts the Skills total from "System tools", so the total never changes when skill |
| [93307](md/93307.md) | 35.0 | o | 0 | 0 | code-review skill: forked children inherit the parent model with no routing, no cost gate on model-i |
| [29000](md/29000.md) | 34.7 | c | 15 | 18 | [BUG] Non-deterministic quota accounting: 65% of 5-hour session consumed with minimal actual token u |
| [53262](md/53262.md) | 34.7 | c | 533 | 93 | HERMES.md in git commit messages causes requests to route to extra usage billing instead of plan quo |
| [50061](md/50061.md) | 34.7 | c | 0 | 5 | `/context` under-reports MCP tool schema consumption (shows 0 tokens per tool, actual ~100K hidden i |
| [86749](md/86749.md) | 34.6 | c | 0 | 2 | [BUG] Claude-generated cron silently used a stale standalone CLI to resume an active VS Code session |
| [16368](md/16368.md) | 34.5 | o | 4 | 5 | [BUG] Maximum call stack exceeded |
| [19959](md/19959.md) | 34.4 | c | 0 | 4 | [DOCS] Fix inaccurate context window calculation logic in status line configuration examples |
| [39841](md/39841.md) | 34.3 | o | 11 | 24 | Opus 1M context on Max plan requires extra usage despite docs saying 'included with subscription' |
| [1756](md/1756.md) | 34.3 | c | 8 | 5 | [BUG] Cost not calculated for LLM Gateway interactions |
| [64153](md/64153.md) | 34.3 | c | 4 | 9 | [BUG] Opus 4.8 medium effort spends 46k output tokens on hidden thinking for a simple coding turn |
| [81924](md/81924.md) | 34.2 | o | 3 | 1 | [BUG] Misleading `plugin-cache-miss` ("not cached at <existing path> — run /plugin to refresh") when |
| [55229](md/55229.md) | 34.2 | c | 1 | 3 | [BUG] Write tool includes full file content in tool_result system-reminder, doubling token cost |
| [21378](md/21378.md) | 34.1 | o | 12 | 9 | 🚨 CRITICAL: Memory leak causes freeze after 20+ minutes (15GB RAM consumption) |
| [38542](md/38542.md) | 34.1 | c | 0 | 3 | Bug: cache_control TTL ordering error when hooks/MCP inject additionalContext into long conversation |
