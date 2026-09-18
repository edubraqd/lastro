# What can actually be saved — the cold ledger

Every number here is the output of `python tools/ledger.py` on one machine's
674 Claude Code sessions (135k API calls, 2026-05 → 2026-09-15), or of a
controlled A/B that is in this repo with its raw data. Nothing is projected.
Where a line is a ceiling rather than a measured saving, it says so.

**Read this first.** The dollars are *API-equivalent at Opus list prices*
(input 5, cache read 0.5, 1h cache write 10, output 25 US$/M — multipliers
confirmed by regression on Claude Code's own `total_cost_usd`, residual 0).
On a subscription you do not pay them; they are the quota you burn. A "saving"
is headroom before the rate limit, not cash, unless you are on API billing.

## The base

| | tokens | US$ | share |
|---|---|---|---|
| cache read | 50.1 B | 25,060 | 62% |
| cache write (1h) | 1.20 B | 11,965 | 30% |
| output | 133 M | 3,318 | 8% |
| uncached input | 4.7 M | 24 | 0% |
| **total** | | **40,367** | |

Context per main-thread call: mean 379k, median 323k, p90 748k (1M window
on, long sessions). Your shares will differ; the mechanisms will not.

## The ledger

| lever | kind of evidence | events | US$ on these logs | % of total | what it would take |
|---|---|---|---|---|---|
| **Not letting the session grow past 200k** | arithmetic ceiling | 95,831 calls above the cap | 13,478 | **33.4%** | This is *only* the cache-read tokens above 200k per call, priced at 0.1×. It is not a forecast: the same work in shorter sessions needs handoffs, re-reads and more prefix writes, none of which is subtracted here. No A/B exists for it in this repo. The literature says pruned history + running summary holds accuracy (Microsoft, arXiv 2606.10209: −63% tokens, 71 → 92% accuracy, *in their setting*). |
| Idle > 60 min, then continuing (TTL re-write) | measured events, priced | 760 | 3,076 | 7.6% | Gross ceiling: every re-write avoided for free. 436 of the 760 came after gaps over 200 min (267 overnight). |
| — captured by a **blind keep-alive pinger** (20 min, 9 pings max) | counterfactual on the same events | 324 reached | **−338** | **−0.8%** | Pays a ping on every idle gap, break or not; the 436 gaps it could not reach are pure cost. Net negative at 3, 6 and 9 pings. Do not run one blind. |
| — captured by pinging **only when you know you'll be back** within 3 h | counterfactual, optimistic | 324 | 880 | 2.2% | Requires knowing in advance which sessions you return to. Upper bound for a smart pinger. |
| — captured by **handoff + `/clear` before leaving** | not an A/B; mechanism measured | 760 | ≤ 3,076 minus ~30k write per return | ≤ 7% | The return costs a ~30k prefix write (US$0.30) instead of a ~400k history re-write (US$4). What is lost is the history in context; the hooks in this repo exist to make that loss cheap. Not measured as a saving because "what you do next" changes. |
| Old-client bug (unexplained full re-writes) | measured events, priced | 793 | 3,254 | 8.1% | **Not actionable.** 418 of them in one session on 2.1.215; ≥ 2.1.237 the rate is 0.1–0.2%. Listed so the 80%-of-writes-are-breaks headline is read correctly: half of it was a bug that no longer reproduces. |
| Hook injecting context on user turns (correlation) | correlation, controls hold | 384 | 1,830 | 4.5% | On current versions (≥ 2.1.237): 12 events, US$31, 0.08%. The correlation is real (0.79% vs 0.06% on current versions, 13×) but the tokens are almost all from old versions. Mechanism unknown; `tools/diverge.py` is the instrument to find it. |
| Tool list / MCP / skills changing mid-session | measured events, priced | 118 | 454 | 1.1% | Avoidable: connect MCP servers and load skills before the long stretch, not during. |
| Resume / model switch | measured events, priced | 77 | 313 | 0.8% | Avoidable by not switching model mid-session; `--resume` is sometimes the point. |
| Effort change mid-session | measured events, priced | 53 | 215 | 0.5% | Avoidable for free: pick the effort before the session (30.8% of effort changes re-wrote the whole history). |
| Terse-output prompting (−8% output) | A/B, Haiku, n = 20, sd 25% | | 265 | 0.7% | Output is 8% of the bill; an 8% cut on it is 0.7%. Measured against a CLAUDE.md that already asks for brevity; against a bare prompt it was +19%. |
| `skillOverrides` (−2,752 prefix tokens per call) | A/B, n = 3 per arm, ±2 tokens | 135k calls | 186 | 0.5% | Free, keep it; not where the money is. Plugin skills ignore it. |
| Trimming `CLAUDE.md` | arithmetic | | Δtokens × calls × 0.5/M | ~0.17% per 1k tokens trimmed | 1k tokens off a project CLAUDE.md saves US$0.0005 per call — US$68 over these 135k calls. A 20.5k-char file (≈ 5k tokens) removed entirely is ~0.8%. |
| `CLAUDE_CODE_COLD_COMPACT` | read the binary, A/B n = 1 | | 0 | 0% | Dead code in 2.1.270. Sets nothing. |
| `promptCacheTtl` / `subagentPromptCacheTtl` | transcript buckets | | 0 / negative | 0% | Main thread was 1h on 100% of writes already; forcing 1h on subagents costs more than the breaks it prevents. |

### What the ledger says, in three lines

1. **Everything you can flip in a settings file together is worth about 2%**
   (skillOverrides, terse output, effort/MCP/model discipline). Do them; they
   are free. Do not expect to see them on the bill.
2. **The only two-digit numbers are about session shape**: how long a session
   runs (33% ceiling, no A/B) and whether you walk away from a large context
   for over an hour (7.6% gross, 0% net with a blind pinger, up to 7% with
   handoff + `/clear`). Both are behaviour, not configuration.
3. **The configuration itself is not a cost centre.** In the controlled A/B
   ([report/ab-config-vs-bare.md](report/ab-config-vs-bare.md)) the full
   configuration was 100% vs 92% accurate, made 40% fewer calls, and cost
   US$0.10 more per *one-task* session because of a 21k prefix write. From
   three tasks per session on, it is the cheaper arm.

## Confidence, per line

- **Measured, priced, on 674 sessions**: TTL, resume, effort, tool-list,
  old-client bug. These are counts of events in the logs with the tokens the
  API reported for them. The only assumption is the price multiplier.
- **Counterfactual on measured events**: the keep-alive lines. They replay a
  policy over the recorded gaps. The policy is simple and stated; the gap
  distribution is real.
- **Controlled A/B**: config vs bare (48 runs), skillOverrides (6 runs),
  terse output (20 runs, weak). Raw data or scripts in the repo.
- **Arithmetic ceiling**: the 200k cap. A sum over the logs, not an
  experiment. Quote it as "the most that mechanism could touch", never as a
  saving.
- **Correlation**: the hook line. Controls hold; mechanism not found.

## What was actually saved, on one machine

The table above is ceilings and counterfactuals. Four working days after the
whole package went in (hooks with the 150k/200k cap, handoff + `/clear`,
`skillOverrides`, terse output), the same transcripts say:

| | before (31/08–13/09, 14 days) | after (14/09–18/09, 5 days) | delta |
|---|---|---|---|
| US$/day | 446 | 188 | **−58%** |
| US$/call | 0.225 | 0.123 | **−45%** |
| context per call, median / p90 | 262k / 595k | 134k / 210k | −49% / −65% |
| calls above 200k | 64% | 13% | |
| calls/day | 1,986 | 1,531 | −23% (17/09 partial; 1.6–2.2k on full days) |
| TTL re-write US$/day | 39 | 9 | |
| autocompact events | 17 | 0 | |

A step on 14/09, not a drift; sessions/day doubled and calls/session halved,
which is the cap doing what it says. The ledger's "33% ceiling" line came out
larger because TTL re-writes and compactions shrink with the context.
`skillOverrides` and terse output are visible (−1k prefix, −24% output) and
still noise on the total. The tool-output compression proxy contributed
nothing: it ran on 0 sessions. Method, per-day table and what it does not
show (quality of work split across sessions) in
[report/usage-real-2026-09-17.md](report/usage-real-2026-09-17.md);
`python tools/before_after.py --split <day>` on your own logs.

## How to get your own numbers

```bash
python tools/ledger.py                       # this table on your transcripts
python tools/ledger.py --cap 150000          # a different session cap
python tools/ledger.py --max-pings 6         # a different pinger policy
python tools/ledger.py --price-input 3       # Sonnet-class prices
python tools/ledger.py --last 100            # only recent sessions (old-client bug drops out)
```

Then [AUDIT.md](AUDIT.md) for how to check each line against the raw
transcripts by hand.
