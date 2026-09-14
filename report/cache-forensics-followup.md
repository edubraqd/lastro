# Follow-up: cross-reference with #42542 and the 2.1.266 string table

*Posted as a comment on [anthropics/claude-code#94177](https://github.com/anthropics/claude-code/issues/94177), 2026-09-13. "Above" refers to [cache-forensics.md](cache-forensics.md).*

Cross-reference and two corrections after reading [#42542](https://github.com/anthropics/claude-code/issues/42542) (silent context degradation — three pruning mechanisms) and the string table of `claude.exe` 2.1.266.

**1. The "4 microcompact events" above are #42542's mechanism (1), and in 2.1.266 the trigger can be server-side.**

#42542 documents three silent prunes: time-based microcompact, cached microcompact (`cache_edits`), and session-memory compact. The four events in section 2.3 match the first one: ~83k of old tool results cleared in place, `cache_read` collapsing to the shared prefix, 620–830k re-written on the next call.

The 2.1.266 binary adds a detail that matters for cache accounting. The microcompact path is reached from the request-error / stream-fallback handlers, not only from a clock:

```
onRequestError(...) → Hs(ll.messages, "microcompact") → "retry:context-hint"
onStreamFallback(...) → Hs(Fu.messages, "microcompact")
tengu_time_based_microcompact { toolsCleared, toolsKept, keepRecent, tokensSaved, trigger: "context_hint" }
"[KEEP-RECENT MC] context_hint trigger, cleared N tool results"
```

So at least one variant is: the client sends the request, the API answers with a context hint, the client clears old tool results and **re-sends**. If the first attempt is billed (I cannot tell from the logs — a hinted retry does not leave two `usage` records), a hinted prune costs one full cold write *plus* whatever the first attempt cost. Either way, the prune is decided one request too late to be cache-aligned. The opt-outs present in the binary are still only `DISABLE_AUTO_COMPACT` and `DISABLE_COMPACT`; there is no independent switch for microcompact, as #42542 asks for.

**2. Correction to suggestion 1 ("cache-aligned compaction"): part of it already exists, so the ask is narrower.**

Two flags in 2.1.266 show the compaction machinery is already cache-aware in two places:

- `tengu_compact_cache_prefix` (default `true`) passes `cacheSafeParams` to the summary request, with `tengu_compact_cache_sharing_success` / `tengu_compact_cache_sharing_fallback` telemetry. The **summary call** reuses the conversation's cached prefix instead of paying a cold write for it.
- `tengu_precomputed_compact_*` (`armFraction`, `autoCompactWindow`, `_ready`, `_persisted`, `_rehydrated`, `_consumed`): the summary is **precomputed** when context reaches an arm fraction and consumed later.

What is still missing is the scheduling: neither flag looks at *when the next request will be cold*. The concrete version of suggestion 1 is therefore: when a precomputed compact is `_ready` and the client can predict a cold request (gap > ~55 min since the last call, model switch, resume), consume it **before** that request rather than at the usual threshold. The write is being paid anyway; the prune rides free. Same for microcompact: prefer a proactive `keepRecent` prune on a predicted-cold call over a hinted retry on a warm one.

**3. One more data point on "resume = only the shared prefix is read" (section 2.4).**

#46603 shows that compaction breaks the `parentUuid` chain in the transcript, so `--resume` reconstructs a different message list than the one that was live. That is a second reason the resumed prefix is not byte-identical to the original beyond the system prompt; suggestion 3 (byte-stable project prefix) does not fix that part — the chain repair proposed in #46603 does.

Caveat as in section 6: all of this is inferred from string constants and telemetry names in the bundled binary, not from source.
