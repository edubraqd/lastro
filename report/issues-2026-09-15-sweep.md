# claude-code issues sweep - 2026-09-15

2356 unique issues from 24 searches. Open: 803. Score = keyword hits + log(reactions) + log(comments) + open bonus.

## cache (1191)

| # | score | st | +1 | cmt | created | title |
|--|--|--|--|--|--|--|
| [89488](https://github.com/anthropics/claude-code/issues/89488) | 98.0 | o | 0 | 0 | 2026-08-25 | [FEATURE] Per-model prompt-cache TTL — extend promptCacheTtl to a per-model map |
| [45381](https://github.com/anthropics/claude-code/issues/45381) | 97.3 | c | 163 | 13 | 2026-04-08 | [BUG] Disabling telemetry also disables 1-hour prompt cache TTL |
| [84289](https://github.com/anthropics/claude-code/issues/84289) | 95.2 | o | 1 | 3 | 2026-08-05 | [DOCS] prompt-caching.md says subagents use the 5-minute TTL, but transcripts show 100% 1- |
| [84253](https://github.com/anthropics/claude-code/issues/84253) | 81.6 | o | 0 | 2 | 2026-08-05 | [BUG] Claude Code 2.1.218+ no longer requests 1h prompt-cache TTL — every 5+ min gap force |
| [34629](https://github.com/anthropics/claude-code/issues/34629) | 79.3 | c | 44 | 25 | 2026-03-15 | [BUG] Prompt cache regression in --print --resume since v2.1.69(?): cache_read never grows |
| [62217](https://github.com/anthropics/claude-code/issues/62217) | 79.1 | c | 0 | 3 | 2026-05-25 | Support configurable prompt cache TTL for subagent launches |
| [46829](https://github.com/anthropics/claude-code/issues/46829) | 78.6 | c | 342 | 56 | 2026-04-12 | Cache TTL silently regressed from 1h to 5m around early March 2026, causing quota and cost |
| [87966](https://github.com/anthropics/claude-code/issues/87966) | 77.6 | o | 0 | 10 | 2026-08-19 | [BUG] Prompt cache lookup fails intermittently mid-session — cache_read pinned to the stab |
| [94177](https://github.com/anthropics/claude-code/issues/94177) | 77.6 | o | 0 | 2 | 2026-09-14 | Prompt-cache forensics from 30 real sessions: 68% of cache writes come from 36 events (TTL |
| [63930](https://github.com/anthropics/claude-code/issues/63930) | 77.1 | c | 7 | 12 | 2026-05-30 | Prompt cache fully re-created after turns with many parallel tool calls (cache_read collap |
| [54006](https://github.com/anthropics/claude-code/issues/54006) | 76.8 | c | 3 | 5 | 2026-04-27 | [BUG] Agent team subagents do not honor 1-hour prompt cache TTL — main sessions show 100%  |
| [14628](https://github.com/anthropics/claude-code/issues/14628) | 75.5 | c | 4 | 5 | 2025-12-19 | [BUG] Prompt Cache TTL Reduced from ~5 to ~3 Minutes Without Documentation (Mid-December 2 |
| [82563](https://github.com/anthropics/claude-code/issues/82563) | 74.6 | o | 0 | 2 | 2026-07-30 | [BUG] Prompt Cache: Full Conversation Prefix Re-written 3 times Seconds Apart (Multiple Se |
| [74318](https://github.com/anthropics/claude-code/issues/74318) | 74.1 | o | 5 | 5 | 2026-07-05 | [FEATURE] Subagent prompt-cache strategy inflates prompt spend ~14% — 3 structural fixes ( |
| [88755](https://github.com/anthropics/claude-code/issues/88755) | 72.9 | o | 0 | 6 | 2026-08-22 | [BUG] Advisor is omitted from internal fork requests, so /compact re-bills the whole conve |
| [29966](https://github.com/anthropics/claude-code/issues/29966) | 72.8 | o | 12 | 7 | 2026-03-02 | Agent SDK subagents have prompt caching disabled by default (enablePromptCaching: false) |
| [83913](https://github.com/anthropics/claude-code/issues/83913) | 72.1 | o | 4 | 8 | 2026-08-04 | Prompt cache invalidated when PreToolUse/PostToolUse additionalContext changes during hist |
| [89621](https://github.com/anthropics/claude-code/issues/89621) | 71.0 | o | 0 | 0 | 2026-08-25 | Prompt cache misses beyond ~16K prefix in long-running subagent with large multimodal cont |
| [77306](https://github.com/anthropics/claude-code/issues/77306) | 70.7 | o | 2 | 4 | 2026-07-13 | [BUG] Session forks (--fork-session / /branch) forfeit the entire conversation prompt cach |
| [56307](https://github.com/anthropics/claude-code/issues/56307) | 69.6 | c | 0 | 2 | 2026-05-05 | [FEATURE] Adaptive cache-TTL heuristic — ~37% of 1h writes don't pay back over 5m |

## compact (311)

| # | score | st | +1 | cmt | created | title |
|--|--|--|--|--|--|--|
| [45756](https://github.com/anthropics/claude-code/issues/45756) | 68.4 | o | 160 | 60 | 2026-04-09 | [BUG] Pro Max 5x Quota Exhausted in 1.5 Hours Despite Moderate Usage |
| [24147](https://github.com/anthropics/claude-code/issues/24147) | 65.7 | o | 15 | 17 | 2026-02-08 | Cache read tokens consume 99.93% of usage quota - architectural scaling issue with CLAUDE. |
| [11008](https://github.com/anthropics/claude-code/issues/11008) | 59.2 | o | 31 | 24 | 2025-11-04 | [FEATURE] Expose token usage and cost data in hook inputs |
| [53065](https://github.com/anthropics/claude-code/issues/53065) | 56.6 | o | 7 | 17 | 2026-04-25 | advisor() tool inflates reported input tokens by forwarding full transcript, triggering pr |
| [38350](https://github.com/anthropics/claude-code/issues/38350) | 49.5 | o | 42 | 63 | 2026-03-24 | [BUG] Abnormal / inflated rate limit / session usage |
| [63015](https://github.com/anthropics/claude-code/issues/63015) | 48.5 | o | 22 | 29 | 2026-05-28 | [Bug] Auto-compact never triggers despite statusline reporting "100% context used" (v2.1.1 |
| [66115](https://github.com/anthropics/claude-code/issues/66115) | 48.2 | o | 16 | 5 | 2026-06-07 | Feature request: auto-compact on idle timeout to prevent cache expiry cost |
| [42542](https://github.com/anthropics/claude-code/issues/42542) | 46.3 | o | 11 | 25 | 2026-04-02 | [BUG] Silent context degradation — tool results cleared without notification on 1M context |
| [33978](https://github.com/anthropics/claude-code/issues/33978) | 46.1 | o | 11 | 21 | 2026-03-13 | [FEATURE] Built-in Usage Analytics Command (claude usage) — Consolidates 10+ Open Issues |
| [34332](https://github.com/anthropics/claude-code/issues/34332) | 45.3 | o | 10 | 7 | 2026-03-14 | Opus 4.6 (1M context): autocompact triggers at ~76K tokens — 92% of context window wasted |
| [40524](https://github.com/anthropics/claude-code/issues/40524) | 44.5 | c | 223 | 124 | 2026-03-29 | [BUG] Conversation history invalidated on subsequent turns |
| [66144](https://github.com/anthropics/claude-code/issues/66144) | 43.7 | o | 25 | 13 | 2026-06-08 | [BUG] Auto compact does not trigger at 100% context window and Claude Code stops itself on |
| [42249](https://github.com/anthropics/claude-code/issues/42249) | 43.4 | o | 17 | 45 | 2026-04-01 | [BUG] Extreme token consumption — quota depleted in minutes with normal usage |
| [6616](https://github.com/anthropics/claude-code/issues/6616) | 43.3 | o | 13 | 18 | 2025-08-26 | Context low warning and /compact failure despite having 86% free context space |
| [91712](https://github.com/anthropics/claude-code/issues/91712) | 43.0 | c | 12 | 8 | 2026-09-03 | Let the Code tab's usage ring report session context, not only the 5-hour window |
| [18456](https://github.com/anthropics/claude-code/issues/18456) | 42.9 | c | 162 | 21 | 2026-01-16 | [FEATURE] VSCode Extension: Display context usage percentage in UI |
| [14258](https://github.com/anthropics/claude-code/issues/14258) | 42.3 | c | 48 | 21 | 2025-12-17 | [FEATURE] PostCompact Hook Event and Compaction Content Control |
| [13783](https://github.com/anthropics/claude-code/issues/13783) | 41.3 | c | 42 | 14 | 2025-12-12 | [BUG] Statusline context_window JSON contains cumulative tokens instead of current context |
| [23751](https://github.com/anthropics/claude-code/issues/23751) | 41.1 | c | 13 | 15 | 2026-02-06 | Compaction fails with 'Conversation too long' at 48% context usage (Opus 4.6) |
| [74473](https://github.com/anthropics/claude-code/issues/74473) | 40.6 | c | 9 | 2 | 2026-07-05 | Bundled claude-api skill injects entire 570KB SKILL.md (~210k tokens) into context on load |

## context (343)

| # | score | st | +1 | cmt | created | title |
|--|--|--|--|--|--|--|
| [45381](https://github.com/anthropics/claude-code/issues/45381) | 97.3 | c | 163 | 13 | 2026-04-08 | [BUG] Disabling telemetry also disables 1-hour prompt cache TTL |
| [46829](https://github.com/anthropics/claude-code/issues/46829) | 78.6 | c | 342 | 56 | 2026-04-12 | Cache TTL silently regressed from 1h to 5m around early March 2026, causing quota and cost |
| [45756](https://github.com/anthropics/claude-code/issues/45756) | 68.4 | o | 160 | 60 | 2026-04-09 | [BUG] Pro Max 5x Quota Exhausted in 1.5 Hours Despite Moderate Usage |
| [46917](https://github.com/anthropics/claude-code/issues/46917) | 66.8 | o | 219 | 41 | 2026-04-12 | CC v2.1.100+ inflates cache_creation by ~20K tokens vs v2.1.98 — same payload, server-side |
| [24147](https://github.com/anthropics/claude-code/issues/24147) | 65.7 | o | 15 | 17 | 2026-02-08 | Cache read tokens consume 99.93% of usage quota - architectural scaling issue with CLAUDE. |
| [11008](https://github.com/anthropics/claude-code/issues/11008) | 59.2 | o | 31 | 24 | 2025-11-04 | [FEATURE] Expose token usage and cost data in hook inputs |
| [41788](https://github.com/anthropics/claude-code/issues/41788) | 49.6 | o | 86 | 60 | 2026-04-01 | Max 20 plan: rate limit 100% exhausted within ~70 minutes after reset (never happened befo |
| [38350](https://github.com/anthropics/claude-code/issues/38350) | 49.5 | o | 42 | 63 | 2026-03-24 | [BUG] Abnormal / inflated rate limit / session usage |
| [63015](https://github.com/anthropics/claude-code/issues/63015) | 48.5 | o | 22 | 29 | 2026-05-28 | [Bug] Auto-compact never triggers despite statusline reporting "100% context used" (v2.1.1 |
| [40524](https://github.com/anthropics/claude-code/issues/40524) | 44.5 | c | 223 | 124 | 2026-03-29 | [BUG] Conversation history invalidated on subsequent turns |
| [66144](https://github.com/anthropics/claude-code/issues/66144) | 43.7 | o | 25 | 13 | 2026-06-08 | [BUG] Auto compact does not trigger at 100% context window and Claude Code stops itself on |
| [18456](https://github.com/anthropics/claude-code/issues/18456) | 42.9 | c | 162 | 21 | 2026-01-16 | [FEATURE] VSCode Extension: Display context usage percentage in UI |
| [13783](https://github.com/anthropics/claude-code/issues/13783) | 41.3 | c | 42 | 14 | 2025-12-12 | [BUG] Statusline context_window JSON contains cumulative tokens instead of current context |
| [17959](https://github.com/anthropics/claude-code/issues/17959) | 40.5 | o | 18 | 5 | 2026-01-13 | context_window.used_percentage doesn't match internal context warning calculation |
| [7111](https://github.com/anthropics/claude-code/issues/7111) | 39.6 | c | 23 | 14 | 2025-09-04 | Feature Request: Restore Time & Token Indicators + Add Context Usage Display |
| [18159](https://github.com/anthropics/claude-code/issues/18159) | 39.4 | o | 15 | 14 | 2026-01-14 | [Bug] Context limit reached with 32k tokens free space and auto-compact disabled |
| [10447](https://github.com/anthropics/claude-code/issues/10447) | 39.2 | o | 55 | 15 | 2025-10-27 | Feature Request: CLI Commands for MCP Server Enable/Disable (Hook Automation Support) |
| [16157](https://github.com/anthropics/claude-code/issues/16157) | 38.7 | o | 725 | 1494 | 2026-01-03 | [BUG] Instantly hitting usage limits with Max subscription |
| [6915](https://github.com/anthropics/claude-code/issues/6915) | 38.6 | c | 378 | 89 | 2025-08-31 | Allow MCP tools to be available only to subagent |
| [33603](https://github.com/anthropics/claude-code/issues/33603) | 38.6 | o | 14 | 19 | 2026-03-12 | CLAUDE.md hard rules and persistent memory instructions consistently ignored — violations  |

## hooks (200)

| # | score | st | +1 | cmt | created | title |
|--|--|--|--|--|--|--|
| [83913](https://github.com/anthropics/claude-code/issues/83913) | 72.1 | o | 4 | 8 | 2026-08-04 | Prompt cache invalidated when PreToolUse/PostToolUse additionalContext changes during hist |
| [45188](https://github.com/anthropics/claude-code/issues/45188) | 57.3 | c | 4 | 9 | 2026-04-08 | System prompt size grew ~70K tokens between v2.1.89 and v2.1.96, making sessions unusable  |
| [40459](https://github.com/anthropics/claude-code/issues/40459) | 53.2 | c | 3 | 14 | 2026-03-29 | v2.1.84+: subagents lose CLAUDE.md context (omitClaudeMd:true), reduced instruction adhere |
| [48734](https://github.com/anthropics/claude-code/issues/48734) | 49.6 | c | 2 | 8 | 2026-04-15 | [BUG] Historical user-message content drift invalidates prompt cache prefix (trailing \n o |
| [43657](https://github.com/anthropics/claude-code/issues/43657) | 49.1 | c | 9 | 15 | 2026-04-04 | [BUG] Resume/continue cache invalidation |
| [77266](https://github.com/anthropics/claude-code/issues/77266) | 44.2 | c | 3 | 1 | 2026-07-13 | [FEATURE] |
| [14258](https://github.com/anthropics/claude-code/issues/14258) | 42.3 | c | 48 | 21 | 2025-12-17 | [FEATURE] PostCompact Hook Event and Compaction Content Control |
| [34556](https://github.com/anthropics/claude-code/issues/34556) | 40.9 | c | 6 | 113 | 2026-03-15 | Feature Request: Persistent Memory Across Context Compactions (59 compactions, built our o |
| [54716](https://github.com/anthropics/claude-code/issues/54716) | 39.6 | c | 11 | 7 | 2026-04-29 | Allow opt-out of built-in deferred tools via settings to reduce baseline context |
| [10447](https://github.com/anthropics/claude-code/issues/10447) | 39.2 | o | 55 | 15 | 2025-10-27 | Feature Request: CLI Commands for MCP Server Enable/Disable (Hook Automation Support) |
| [2511](https://github.com/anthropics/claude-code/issues/2511) | 38.3 | o | 639 | 50 | 2025-06-24 | Feature request: Connect Claude code to Claude projects  |
| [6235](https://github.com/anthropics/claude-code/issues/6235) | 37.4 | c | 6626 | 394 | 2025-08-21 | Feature Request: Support AGENTS.md. |
| [34650](https://github.com/anthropics/claude-code/issues/34650) | 36.8 | c | 25 | 14 | 2026-03-15 | Add --max-context flag to cap context window usage |
| [19471](https://github.com/anthropics/claude-code/issues/19471) | 32.0 | c | 9 | 28 | 2026-01-20 | [BUG] CLAUDE.md instructions completely ignored after context compaction |
| [29330](https://github.com/anthropics/claude-code/issues/29330) | 31.3 | c | 7 | 14 | 2026-02-27 | [BUG] Opus 1M context window suddenly returns "Rate limit reached" on both Max and Team pl |
| [28469](https://github.com/anthropics/claude-code/issues/28469) | 30.5 | o | 18 | 22 | 2026-02-25 | Opus 4.6 comprehensive regression: loops, memory loss, ignored instructions - daily profes |
| [33088](https://github.com/anthropics/claude-code/issues/33088) | 30.5 | c | 3 | 8 | 2026-03-11 | [Feature] Graceful context compaction — PreCompact hook data + background compaction optio |
| [12633](https://github.com/anthropics/claude-code/issues/12633) | 29.7 | o | 29 | 9 | 2025-11-28 | [FEATURE] Allow skills to be hidden from the main agent (subagent-exclusive skills) |
| [30280](https://github.com/anthropics/claude-code/issues/30280) | 29.6 | o | 13 | 11 | 2026-03-03 | Sub-agents spawned via Agent tool don't reliably inherit MCP tools (inconsistent with docs |
| [24057](https://github.com/anthropics/claude-code/issues/24057) | 29.5 | o | 20 | 34 | 2026-02-08 | MCP servers, hooks, and plugins should auto-reload when config changes — no restart needed |

## prefix (589)

| # | score | st | +1 | cmt | created | title |
|--|--|--|--|--|--|--|
| [45381](https://github.com/anthropics/claude-code/issues/45381) | 97.3 | c | 163 | 13 | 2026-04-08 | [BUG] Disabling telemetry also disables 1-hour prompt cache TTL |
| [34629](https://github.com/anthropics/claude-code/issues/34629) | 79.3 | c | 44 | 25 | 2026-03-15 | [BUG] Prompt cache regression in --print --resume since v2.1.69(?): cache_read never grows |
| [46829](https://github.com/anthropics/claude-code/issues/46829) | 78.6 | c | 342 | 56 | 2026-04-12 | Cache TTL silently regressed from 1h to 5m around early March 2026, causing quota and cost |
| [87966](https://github.com/anthropics/claude-code/issues/87966) | 77.6 | o | 0 | 10 | 2026-08-19 | [BUG] Prompt cache lookup fails intermittently mid-session — cache_read pinned to the stab |
| [29966](https://github.com/anthropics/claude-code/issues/29966) | 72.8 | o | 12 | 7 | 2026-03-02 | Agent SDK subagents have prompt caching disabled by default (enablePromptCaching: false) |
| [77306](https://github.com/anthropics/claude-code/issues/77306) | 70.7 | o | 2 | 4 | 2026-07-13 | [BUG] Session forks (--fork-session / /branch) forfeit the entire conversation prompt cach |
| [45756](https://github.com/anthropics/claude-code/issues/45756) | 68.4 | o | 160 | 60 | 2026-04-09 | [BUG] Pro Max 5x Quota Exhausted in 1.5 Hours Despite Moderate Usage |
| [93499](https://github.com/anthropics/claude-code/issues/93499) | 68.1 | o | 1 | 1 | 2026-09-11 | [FEATURE] Cache CLAUDE.md and rules across sessions: they are re-written to the prompt cac |
| [81967](https://github.com/anthropics/claude-code/issues/81967) | 67.9 | o | 0 | 6 | 2026-07-28 | [Bug] Prompt cache invalidation: tools array mutation and TTL downgrade during session |
| [46917](https://github.com/anthropics/claude-code/issues/46917) | 66.8 | o | 219 | 41 | 2026-04-12 | CC v2.1.100+ inflates cache_creation by ~20K tokens vs v2.1.98 — same payload, server-side |
| [24147](https://github.com/anthropics/claude-code/issues/24147) | 65.7 | o | 15 | 17 | 2026-02-08 | Cache read tokens consume 99.93% of usage quota - architectural scaling issue with CLAUDE. |
| [92033](https://github.com/anthropics/claude-code/issues/92033) | 64.7 | o | 2 | 4 | 2026-09-04 | Mid-conversation tool/MCP list changes silently invalidate prompt cache, causing repeated  |
| [68140](https://github.com/anthropics/claude-code/issues/68140) | 64.3 | c | 7 | 1 | 2026-06-13 | [BUG] TodoWrite re-stamps a front-of-context block on every update, invalidating the entir |
| [27048](https://github.com/anthropics/claude-code/issues/27048) | 63.8 | c | 0 | 12 | 2026-02-20 | [BUG] Prompt Cache Invalidation on Session Resume: Tool-Use Content Not Cached, Plugin Sta |
| [90584](https://github.com/anthropics/claude-code/issues/90584) | 63.0 | o | 0 | 0 | 2026-08-29 | MCP tool_reference scrub invalidates the prompt cache when servers are still `pending` on  |
| [49038](https://github.com/anthropics/claude-code/issues/49038) | 60.9 | c | 0 | 6 | 2026-04-16 | Prompt cache miss on resume: Agent tool description enumerates sub-agents in non-determini |
| [61984](https://github.com/anthropics/claude-code/issues/61984) | 60.6 | c | 0 | 2 | 2026-05-24 | Docs: `/effort` changes documented as "no effect on the cache" but empirically cause full/ |
| [91514](https://github.com/anthropics/claude-code/issues/91514) | 60.1 | o | 0 | 3 | 2026-09-02 | [BUG] Warm prompt cache fully re-written (cache_read collapses to system+tools floor) seco |
| [11008](https://github.com/anthropics/claude-code/issues/11008) | 59.2 | o | 31 | 24 | 2025-11-04 | [FEATURE] Expose token usage and cost data in hook inputs |
| [40652](https://github.com/anthropics/claude-code/issues/40652) | 59.0 | c | 13 | 14 | 2026-03-29 | CLI mutates historical tool results via cch= billing hash substitution, permanently breaki |

## subagent (200)

| # | score | st | +1 | cmt | created | title |
|--|--|--|--|--|--|--|
| [45381](https://github.com/anthropics/claude-code/issues/45381) | 97.3 | c | 163 | 13 | 2026-04-08 | [BUG] Disabling telemetry also disables 1-hour prompt cache TTL |
| [46829](https://github.com/anthropics/claude-code/issues/46829) | 78.6 | c | 342 | 56 | 2026-04-12 | Cache TTL silently regressed from 1h to 5m around early March 2026, causing quota and cost |
| [63930](https://github.com/anthropics/claude-code/issues/63930) | 77.1 | c | 7 | 12 | 2026-05-30 | Prompt cache fully re-created after turns with many parallel tool calls (cache_read collap |
| [74318](https://github.com/anthropics/claude-code/issues/74318) | 74.1 | o | 5 | 5 | 2026-07-05 | [FEATURE] Subagent prompt-cache strategy inflates prompt spend ~14% — 3 structural fixes ( |
| [29966](https://github.com/anthropics/claude-code/issues/29966) | 72.8 | o | 12 | 7 | 2026-03-02 | Agent SDK subagents have prompt caching disabled by default (enablePromptCaching: false) |
| [45756](https://github.com/anthropics/claude-code/issues/45756) | 68.4 | o | 160 | 60 | 2026-04-09 | [BUG] Pro Max 5x Quota Exhausted in 1.5 Hours Despite Moderate Usage |
| [46917](https://github.com/anthropics/claude-code/issues/46917) | 66.8 | o | 219 | 41 | 2026-04-12 | CC v2.1.100+ inflates cache_creation by ~20K tokens vs v2.1.98 — same payload, server-side |
| [11008](https://github.com/anthropics/claude-code/issues/11008) | 59.2 | o | 31 | 24 | 2025-11-04 | [FEATURE] Expose token usage and cost data in hook inputs |
| [53065](https://github.com/anthropics/claude-code/issues/53065) | 56.6 | o | 7 | 17 | 2026-04-25 | advisor() tool inflates reported input tokens by forwarding full transcript, triggering pr |
| [41788](https://github.com/anthropics/claude-code/issues/41788) | 49.6 | o | 86 | 60 | 2026-04-01 | Max 20 plan: rate limit 100% exhausted within ~70 minutes after reset (never happened befo |
| [38350](https://github.com/anthropics/claude-code/issues/38350) | 49.5 | o | 42 | 63 | 2026-03-24 | [BUG] Abnormal / inflated rate limit / session usage |
| [42542](https://github.com/anthropics/claude-code/issues/42542) | 46.3 | o | 11 | 25 | 2026-04-02 | [BUG] Silent context degradation — tool results cleared without notification on 1M context |
| [33978](https://github.com/anthropics/claude-code/issues/33978) | 46.1 | o | 11 | 21 | 2026-03-13 | [FEATURE] Built-in Usage Analytics Command (claude usage) — Consolidates 10+ Open Issues |
| [40524](https://github.com/anthropics/claude-code/issues/40524) | 44.5 | c | 223 | 124 | 2026-03-29 | [BUG] Conversation history invalidated on subsequent turns |
| [54750](https://github.com/anthropics/claude-code/issues/54750) | 41.3 | o | 12 | 20 | 2026-04-29 | Bug: Claude Code current session limit reaches 100% despite low visible local session usag |
| [68147](https://github.com/anthropics/claude-code/issues/68147) | 41.3 | c | 7 | 3 | 2026-06-13 | Subagent model override silently dropped after a continuation boundary (SendMessage follow |
| [23751](https://github.com/anthropics/claude-code/issues/23751) | 41.1 | c | 13 | 15 | 2026-02-06 | Compaction fails with 'Conversation too long' at 48% context usage (Opus 4.6) |
| [22625](https://github.com/anthropics/claude-code/issues/22625) | 41.0 | c | 9 | 3 | 2026-02-02 | [FEATURE] Per-Subagent Token Usage Tracking |
| [34556](https://github.com/anthropics/claude-code/issues/34556) | 40.9 | c | 6 | 113 | 2026-03-15 | Feature Request: Persistent Memory Across Context Compactions (59 compactions, built our o |
| [21567](https://github.com/anthropics/claude-code/issues/21567) | 40.3 | o | 15 | 13 | 2026-01-28 | Terminal renderer CPU spin: 100% CPU with 625K writes/0 blits on large session |

## usage (558)

| # | score | st | +1 | cmt | created | title |
|--|--|--|--|--|--|--|
| [34629](https://github.com/anthropics/claude-code/issues/34629) | 79.3 | c | 44 | 25 | 2026-03-15 | [BUG] Prompt cache regression in --print --resume since v2.1.69(?): cache_read never grows |
| [46829](https://github.com/anthropics/claude-code/issues/46829) | 78.6 | c | 342 | 56 | 2026-04-12 | Cache TTL silently regressed from 1h to 5m around early March 2026, causing quota and cost |
| [94177](https://github.com/anthropics/claude-code/issues/94177) | 77.6 | o | 0 | 2 | 2026-09-14 | Prompt-cache forensics from 30 real sessions: 68% of cache writes come from 36 events (TTL |
| [54006](https://github.com/anthropics/claude-code/issues/54006) | 76.8 | c | 3 | 5 | 2026-04-27 | [BUG] Agent team subagents do not honor 1-hour prompt cache TTL — main sessions show 100%  |
| [82563](https://github.com/anthropics/claude-code/issues/82563) | 74.6 | o | 0 | 2 | 2026-07-30 | [BUG] Prompt Cache: Full Conversation Prefix Re-written 3 times Seconds Apart (Multiple Se |
| [13997](https://github.com/anthropics/claude-code/issues/13997) | 68.8 | c | 1 | 5 | 2025-12-15 | The bug: BqA() in cli.js counts cache_creation_input_tokens and cache_read_input_tokens to |
| [45756](https://github.com/anthropics/claude-code/issues/45756) | 68.4 | o | 160 | 60 | 2026-04-09 | [BUG] Pro Max 5x Quota Exhausted in 1.5 Hours Despite Moderate Usage |
| [46917](https://github.com/anthropics/claude-code/issues/46917) | 66.8 | o | 219 | 41 | 2026-04-12 | CC v2.1.100+ inflates cache_creation by ~20K tokens vs v2.1.98 — same payload, server-side |
| [24147](https://github.com/anthropics/claude-code/issues/24147) | 65.7 | o | 15 | 17 | 2026-02-08 | Cache read tokens consume 99.93% of usage quota - architectural scaling issue with CLAUDE. |
| [11008](https://github.com/anthropics/claude-code/issues/11008) | 59.2 | o | 31 | 24 | 2025-11-04 | [FEATURE] Expose token usage and cost data in hook inputs |
| [53065](https://github.com/anthropics/claude-code/issues/53065) | 56.6 | o | 7 | 17 | 2026-04-25 | advisor() tool inflates reported input tokens by forwarding full transcript, triggering pr |
| [18726](https://github.com/anthropics/claude-code/issues/18726) | 55.1 | c | 0 | 3 | 2026-01-17 | [DOCS] Clarify "Worst-Case" cost estimation in Token Counting API regarding Prompt Caching |
| [66005](https://github.com/anthropics/claude-code/issues/66005) | 53.7 | o | 2 | 9 | 2026-06-07 | [BUG] `--resume` drops the session's `--effort` level, invalidating the prompt cache |
| [59650](https://github.com/anthropics/claude-code/issues/59650) | 53.6 | c | 0 | 2 | 2026-05-16 | Deferred MCP tool schemas inflate cache reads and per-turn token counts unnecessarily |
| [28167](https://github.com/anthropics/claude-code/issues/28167) | 51.2 | c | 4 | 4 | 2026-02-24 | Context usage percentage only counts input tokens, causing misleading 'Context limit reach |
| [41788](https://github.com/anthropics/claude-code/issues/41788) | 49.6 | o | 86 | 60 | 2026-04-01 | Max 20 plan: rate limit 100% exhausted within ~70 minutes after reset (never happened befo |
| [38350](https://github.com/anthropics/claude-code/issues/38350) | 49.5 | o | 42 | 63 | 2026-03-24 | [BUG] Abnormal / inflated rate limit / session usage |
| [49302](https://github.com/anthropics/claude-code/issues/49302) | 48.5 | c | 5 | 7 | 2026-04-16 | [Bug] Opus 4.7 metering: cache_read_input_tokens consuming 5-hour bucket at input-token ra |
| [46422](https://github.com/anthropics/claude-code/issues/46422) | 48.1 | c | 0 | 3 | 2026-04-10 | [BUG] Token estimation vs API-reported tokens diverge significantly for cached context |
| [59975](https://github.com/anthropics/claude-code/issues/59975) | 46.4 | c | 0 | 4 | 2026-05-17 | [FEATURE] Expose runtime metadata (token usage, context %, compaction status) to the model |

## top 60 overall

| # | score | st | +1 | cmt | created | title |
|--|--|--|--|--|--|--|
| [89488](https://github.com/anthropics/claude-code/issues/89488) | 98.0 | o | 0 | 0 | 2026-08-25 | [FEATURE] Per-model prompt-cache TTL — extend promptCacheTtl to a per-model map |
| [45381](https://github.com/anthropics/claude-code/issues/45381) | 97.3 | c | 163 | 13 | 2026-04-08 | [BUG] Disabling telemetry also disables 1-hour prompt cache TTL |
| [84289](https://github.com/anthropics/claude-code/issues/84289) | 95.2 | o | 1 | 3 | 2026-08-05 | [DOCS] prompt-caching.md says subagents use the 5-minute TTL, but transcripts show 100% 1- |
| [84253](https://github.com/anthropics/claude-code/issues/84253) | 81.6 | o | 0 | 2 | 2026-08-05 | [BUG] Claude Code 2.1.218+ no longer requests 1h prompt-cache TTL — every 5+ min gap force |
| [34629](https://github.com/anthropics/claude-code/issues/34629) | 79.3 | c | 44 | 25 | 2026-03-15 | [BUG] Prompt cache regression in --print --resume since v2.1.69(?): cache_read never grows |
| [62217](https://github.com/anthropics/claude-code/issues/62217) | 79.1 | c | 0 | 3 | 2026-05-25 | Support configurable prompt cache TTL for subagent launches |
| [46829](https://github.com/anthropics/claude-code/issues/46829) | 78.6 | c | 342 | 56 | 2026-04-12 | Cache TTL silently regressed from 1h to 5m around early March 2026, causing quota and cost |
| [87966](https://github.com/anthropics/claude-code/issues/87966) | 77.6 | o | 0 | 10 | 2026-08-19 | [BUG] Prompt cache lookup fails intermittently mid-session — cache_read pinned to the stab |
| [94177](https://github.com/anthropics/claude-code/issues/94177) | 77.6 | o | 0 | 2 | 2026-09-14 | Prompt-cache forensics from 30 real sessions: 68% of cache writes come from 36 events (TTL |
| [63930](https://github.com/anthropics/claude-code/issues/63930) | 77.1 | c | 7 | 12 | 2026-05-30 | Prompt cache fully re-created after turns with many parallel tool calls (cache_read collap |
| [54006](https://github.com/anthropics/claude-code/issues/54006) | 76.8 | c | 3 | 5 | 2026-04-27 | [BUG] Agent team subagents do not honor 1-hour prompt cache TTL — main sessions show 100%  |
| [14628](https://github.com/anthropics/claude-code/issues/14628) | 75.5 | c | 4 | 5 | 2025-12-19 | [BUG] Prompt Cache TTL Reduced from ~5 to ~3 Minutes Without Documentation (Mid-December 2 |
| [82563](https://github.com/anthropics/claude-code/issues/82563) | 74.6 | o | 0 | 2 | 2026-07-30 | [BUG] Prompt Cache: Full Conversation Prefix Re-written 3 times Seconds Apart (Multiple Se |
| [74318](https://github.com/anthropics/claude-code/issues/74318) | 74.1 | o | 5 | 5 | 2026-07-05 | [FEATURE] Subagent prompt-cache strategy inflates prompt spend ~14% — 3 structural fixes ( |
| [88755](https://github.com/anthropics/claude-code/issues/88755) | 72.9 | o | 0 | 6 | 2026-08-22 | [BUG] Advisor is omitted from internal fork requests, so /compact re-bills the whole conve |
| [29966](https://github.com/anthropics/claude-code/issues/29966) | 72.8 | o | 12 | 7 | 2026-03-02 | Agent SDK subagents have prompt caching disabled by default (enablePromptCaching: false) |
| [83913](https://github.com/anthropics/claude-code/issues/83913) | 72.1 | o | 4 | 8 | 2026-08-04 | Prompt cache invalidated when PreToolUse/PostToolUse additionalContext changes during hist |
| [89621](https://github.com/anthropics/claude-code/issues/89621) | 71.0 | o | 0 | 0 | 2026-08-25 | Prompt cache misses beyond ~16K prefix in long-running subagent with large multimodal cont |
| [77306](https://github.com/anthropics/claude-code/issues/77306) | 70.7 | o | 2 | 4 | 2026-07-13 | [BUG] Session forks (--fork-session / /branch) forfeit the entire conversation prompt cach |
| [56307](https://github.com/anthropics/claude-code/issues/56307) | 69.6 | c | 0 | 2 | 2026-05-05 | [FEATURE] Adaptive cache-TTL heuristic — ~37% of 1h writes don't pay back over 5m |
| [64901](https://github.com/anthropics/claude-code/issues/64901) | 69.1 | c | 0 | 3 | 2026-06-03 | [BUG] Async sub-agent completion can rebuild warm prompt cache, quickly burning usage limi |
| [13997](https://github.com/anthropics/claude-code/issues/13997) | 68.8 | c | 1 | 5 | 2025-12-15 | The bug: BqA() in cli.js counts cache_creation_input_tokens and cache_read_input_tokens to |
| [45756](https://github.com/anthropics/claude-code/issues/45756) | 68.4 | o | 160 | 60 | 2026-04-09 | [BUG] Pro Max 5x Quota Exhausted in 1.5 Hours Despite Moderate Usage |
| [70459](https://github.com/anthropics/claude-code/issues/70459) | 68.3 | o | 3 | 7 | 2026-06-23 | Auto-compaction: two compounding cost bugs — stale precompute keeps ~200k tokens verbatim, |
| [93499](https://github.com/anthropics/claude-code/issues/93499) | 68.1 | o | 1 | 1 | 2026-09-11 | [FEATURE] Cache CLAUDE.md and rules across sessions: they are re-written to the prompt cac |
| [51218](https://github.com/anthropics/claude-code/issues/51218) | 68.0 | c | 1 | 6 | 2026-04-20 | [BUG] Prompt cache expires during active session, causing massive token spikes on next pro |
| [81967](https://github.com/anthropics/claude-code/issues/81967) | 67.9 | o | 0 | 6 | 2026-07-28 | [Bug] Prompt cache invalidation: tools array mutation and TTL downgrade during session |
| [60316](https://github.com/anthropics/claude-code/issues/60316) | 66.9 | c | 7 | 2 | 2026-05-18 | Expose `cache_control.ttl` (5m / 1h) as a user-configurable setting |
| [46917](https://github.com/anthropics/claude-code/issues/46917) | 66.8 | o | 219 | 41 | 2026-04-12 | CC v2.1.100+ inflates cache_creation by ~20K tokens vs v2.1.98 — same payload, server-side |
| [91706](https://github.com/anthropics/claude-code/issues/91706) | 66.0 | o | 0 | 0 | 2026-09-03 | [BUG] A persisting `cd` in a Bash tool call re-resolves project context and rewrites the s |
| [24147](https://github.com/anthropics/claude-code/issues/24147) | 65.7 | o | 15 | 17 | 2026-02-08 | Cache read tokens consume 99.93% of usage quota - architectural scaling issue with CLAUDE. |
| [92033](https://github.com/anthropics/claude-code/issues/92033) | 64.7 | o | 2 | 4 | 2026-09-04 | Mid-conversation tool/MCP list changes silently invalidate prompt cache, causing repeated  |
| [68140](https://github.com/anthropics/claude-code/issues/68140) | 64.3 | c | 7 | 1 | 2026-06-13 | [BUG] TodoWrite re-stamps a front-of-context block on every update, invalidating the entir |
| [47425](https://github.com/anthropics/claude-code/issues/47425) | 64.2 | o | 10 | 1 | 2026-04-13 | Feature request: intermediate prompt cache TTL tiers (15m, 30m) for interactive use |
| [27048](https://github.com/anthropics/claude-code/issues/27048) | 63.8 | c | 0 | 12 | 2026-02-20 | [BUG] Prompt Cache Invalidation on Session Resume: Tool-Use Content Not Cached, Plugin Sta |
| [29876](https://github.com/anthropics/claude-code/issues/29876) | 63.7 | c | 4 | 6 | 2026-03-01 | Unexpected 2x token burn rate on MAX plan - possibly related to recent prompt caching chan |
| [77001](https://github.com/anthropics/claude-code/issues/77001) | 63.7 | o | 0 | 5 | 2026-07-12 | Disproportionate subscription usage burn in long sessions: cache TTL expiry re-writes + no |
| [87215](https://github.com/anthropics/claude-code/issues/87215) | 63.6 | o | 0 | 2 | 2026-08-16 | [BUG] Waking a parked subagent re-caches its entire context: only the system prefix is ser |
| [90584](https://github.com/anthropics/claude-code/issues/90584) | 63.0 | o | 0 | 0 | 2026-08-29 | MCP tool_reference scrub invalidates the prompt cache when servers are still `pending` on  |
| [44724](https://github.com/anthropics/claude-code/issues/44724) | 62.6 | c | 0 | 10 | 2026-04-07 | Subagent cache miss on first SendMessage resume (cache_read=0) |
| [63962](https://github.com/anthropics/claude-code/issues/63962) | 60.9 | c | 7 | 5 | 2026-05-30 | [BUG] /effort change confirmation dialog warns about cache miss, but cache is preserved |
| [49038](https://github.com/anthropics/claude-code/issues/49038) | 60.9 | c | 0 | 6 | 2026-04-16 | Prompt cache miss on resume: Agent tool description enumerates sub-agents in non-determini |
| [61984](https://github.com/anthropics/claude-code/issues/61984) | 60.6 | c | 0 | 2 | 2026-05-24 | Docs: `/effort` changes documented as "no effect on the cache" but empirically cause full/ |
| [91705](https://github.com/anthropics/claude-code/issues/91705) | 60.6 | c | 0 | 2 | 2026-09-03 | [BUG] A pasted image is re-rendered as a file pointer on the next request: one full prompt |
| [91514](https://github.com/anthropics/claude-code/issues/91514) | 60.1 | o | 0 | 3 | 2026-09-02 | [BUG] Warm prompt cache fully re-written (cache_read collapses to system+tools floor) seco |
| [5904](https://github.com/anthropics/claude-code/issues/5904) | 59.9 | c | 20 | 11 | 2025-08-16 | [BUG] Local /cost doubles usage when parsing session JSONL (cache write & I/O tokens; ~2×  |
| [90018](https://github.com/anthropics/claude-code/issues/90018) | 59.8 | o | 3 | 2 | 2026-08-27 | [BUG] totalTokensReminder causes repeatable prompt-cache floor in tool loops; off restores |
| [90009](https://github.com/anthropics/claude-code/issues/90009) | 59.6 | o | 0 | 2 | 2026-08-27 | [BUG] Forking from unprimed post-compact context re-bills the full shared prefix twice (fo |
| [63981](https://github.com/anthropics/claude-code/issues/63981) | 59.4 | c | 0 | 4 | 2026-05-30 | Multi-lane Workflow agents re-create shared prompt cache per lane (no cross-sibling sharin |
| [11008](https://github.com/anthropics/claude-code/issues/11008) | 59.2 | o | 31 | 24 | 2025-11-04 | [FEATURE] Expose token usage and cost data in hook inputs |
| [36243](https://github.com/anthropics/claude-code/issues/36243) | 59.2 | c | 1 | 3 | 2026-03-19 | [BUG] ENABLE_PROMPT_CACHING_1H_BEDROCK does not apply 1h TTL to subagent requests |
| [88412](https://github.com/anthropics/claude-code/issues/88412) | 59.1 | c | 0 | 3 | 2026-08-21 | [BUG] Waking an idle agent fork (`subagent_type: "fork"`) forfeits its inherited prompt ca |
| [40652](https://github.com/anthropics/claude-code/issues/40652) | 59.0 | c | 13 | 14 | 2026-03-29 | CLI mutates historical tool results via cch= billing hash substitution, permanently breaki |
| [76058](https://github.com/anthropics/claude-code/issues/76058) | 59.0 | o | 0 | 0 | 2026-07-09 | [BUG] 1h prompt cache intermittently invalidated every ~11-12 min in active sessions, full |
| [51764](https://github.com/anthropics/claude-code/issues/51764) | 58.2 | c | 1 | 3 | 2026-04-21 | `--continue`/`--resume` cache invalidation still reproduces on v2.1.116 — TTL-matched cont |
| [92938](https://github.com/anthropics/claude-code/issues/92938) | 58.0 | o | 0 | 0 | 2026-09-08 | [BUG] Prompt cache for resumed session history intermittently fails to hit on `resume`, in |
| [65636](https://github.com/anthropics/claude-code/issues/65636) | 57.9 | c | 0 | 6 | 2026-06-05 | [BUG] Oversized-image 400 error triggers a retry loop that invalidates prompt cache and in |
| [27786](https://github.com/anthropics/claude-code/issues/27786) | 57.5 | c | 1 | 4 | 2026-02-23 | Agent SDK: prompt cache invalidated every query() — random UUID in Bash tool description |
| [45188](https://github.com/anthropics/claude-code/issues/45188) | 57.3 | c | 4 | 9 | 2026-04-08 | System prompt size grew ~70K tokens between v2.1.89 and v2.1.96, making sessions unusable  |
| [77360](https://github.com/anthropics/claude-code/issues/77360) | 57.1 | o | 0 | 3 | 2026-07-14 | Browser automation in near-1M-token sessions silently burns extreme token volume (~43M cac |
