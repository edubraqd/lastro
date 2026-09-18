# How to audit every number in this repo

The claim of this repo is not "we saved X". It is "these events happened in
these logs, and at these prices they add up to X". This page tells you where
each number comes from and how to check it without trusting a script.

## 0. The raw material

Claude Code writes one transcript per session:
`~/.claude/projects/<cwd with non-alphanumerics replaced by '-'>/<session-id>.jsonl`
(`CLAUDE_CONFIG_DIR` overrides `~/.claude`). One JSON object per line. The
lines that matter for cost have `"type": "assistant"` and a
`message.usage` block:

```json
{"type":"assistant","timestamp":"2026-09-14T22:51:03.120Z","version":"2.1.272",
 "requestId":"req_...","isSidechain":false,
 "message":{"id":"msg_...","model":"claude-opus-5",
   "usage":{"input_tokens":4,"cache_creation_input_tokens":21363,"cache_read_input_tokens":87719,
            "output_tokens":312,
            "cache_creation":{"ephemeral_5m_input_tokens":0,"ephemeral_1h_input_tokens":21363}}}}
```

Everything in the reports is a sum, count or ratio over these fields, plus
the `timestamp` (for gaps), `version`, `model`, `isSidechain` (subagent
calls), and the `attachment` / `system` lines that sit between two assistant
lines (what happened in the client between two API calls).

## 1. The one rule: deduplicate

Claude Code writes **one `assistant` line per content block** (thinking,
text, each `tool_use`), and every line of the same API call carries the
**same** `usage`. Sum per line and you over-count ~1.7×. Dedup by
`(message.id, requestId)`. Check it yourself on one transcript:

```bash
F=~/.claude/projects/<project>/<session>.jsonl
grep -c '"usage"' $F                                            # lines
grep -o '"id":"msg_[^"]*"' $F | sort -u | wc -l                 # API calls
```

Then, a resumed or forked session **copies the whole transcript** into a new
file, so the same calls appear in two files. `tools/sessions.py` keeps one
`seen` set across every file it reads, oldest file first. If you write your
own counter, do the same, or your totals will be inflated by every `--resume`.

## 2. Prices

The multipliers are Anthropic's published ones: cache read 0.1×, 5-minute
cache write 1.25×, 1-hour cache write 2×, output 5× the input price. They
were **recovered, not assumed**: `experiments/ab-config-vs-bare/decomp.py`
fits Claude Code's own `total_cost_usd` (from `--output-format json`) against
the five counters summed per run; the maximum residual over 48 runs was
0.0000. On 2026-09-14 that gave input 5 / cw-1h 10 / cr 0.5 / out 25 US$/M
(no 5m writes occurred, so that column is unidentified in this fit). If
Anthropic changes prices, the fit changes; rerun it rather than editing the
constants.

`tools/ledger.py --price-input P` rescales everything to another model class.

## 3. Reproducing each headline

| claim | where it is | how to check |
|---|---|---|
| cache read 62% / write 30% / output 8% | findings §2, SAVINGS | `python tools/sessions.py --last 0 --min-calls 5` → last block. Multiply the token totals by the multipliers yourself. |
| jsonl overstates 1.7× | findings §1 | §1 above on any long transcript. |
| gap ≥ 60 min breaks 93–97%, < 20 min ≤ 7% | findings §3 | `python tools/ttl.py --last 0`. Definition: consecutive main-thread calls, previous context ≥ 20k, "broke" = `cache_creation` > 20% of previous context and > 20k. Change the thresholds in the script and see that the cliff at 60 min does not move. |
| a cache hit refreshes the 1h TTL | findings §3 | Needs the proxy: `tools/wrap-cache.sh`, wait 21 min, check `~/.claude/cache-proxy.log` for `cc 0` on the ping, then a hit at 61 min. One afternoon. |
| blind keep-alive is net negative | findings §3, SAVINGS | `python tools/ledger.py --max-pings 9` → the two `ttl-keepalive-net` lines. The policy is 8 lines in `ledger.py` (search `pings =`); the events it credits are the `ttl` line of `tools/breaks.py --last 0`. Vary `--ping-every` and `--max-pings`. |
| breaks by cause (ttl / resume / partial …) | findings §4 | `python tools/breaks.py --last 0`. `classify()` in `breaks.py` is 15 lines; read it, then pick any row of the "largest 15" and open that transcript at that call number. |
| effort change re-writes 31% | findings §4.1 | `python tools/rewrites.py --last 0`, row `attachment:ultra_effort_enter`. n and rate are printed for every event type; the baseline is the `(all)` line. |
| hook context correlation (20×; 13× on current versions) | findings §4.1, SAVINGS | same script, rows `attachment:hook_additional_context`; the controlled split (hook / no hook × old / current) is in `tools/ledger.py` output, last block. |
| old-client bug (2.1.215: 32.5%) | findings §4.1 | `rewrites.py` "by version" block. Then `--last 100`: the bucket disappears on current versions. |
| skillOverrides −2,752 tokens | findings §5 | Rename `.claude/settings.json` between arms; `claude -p "reply only: ok" --max-turns 1 --output-format json` ×3 each; compare `usage.cache_creation_input_tokens` on the first call. Variance was ±2 tokens. |
| COLD_COMPACT is dead code | findings §6 | Strings in the binary + the A/B recipe in §6. Not re-checkable without a copy of 2.1.270; the recipe to force a compaction is there for later versions. |
| terse output −8% | findings §7 | Script and prompts in [JuliusBrussee/caveman#1044](https://github.com/JuliusBrussee/caveman/pull/1044). n = 20, sd 25%: the weakest number in the repo, and it is 0.7% of the bill either way. |
| CLAUDE.md never shared across sessions | findings §9 | `python tools/first_call.py` → warm starts (< 60 min after another session in the same dir) show `cr` = 46,328 + a per-project constant, never larger. To see *why*, capture two bodies through the proxy and `python tools/diverge.py`. |
| main thread always 1h, subagents always 5m | findings §10 | `python tools/ledger.py` → "cache writes by TTL bucket". Fields `usage.cache_creation.ephemeral_{5m,1h}_input_tokens` × `isSidechain`. |
| config vs bare: 24/24 vs 22/24, 24/24 more expensive, break-even 3 tasks | report/ab-config-vs-bare.md | `experiments/ab-config-vs-bare/data/results-2026-09-14.jsonl` has all 48 runs (cost, usage, verdict, session id; answer text stripped). `python analyze.py data/results-2026-09-14.jsonl` reproduces the tables. `decomp.py` needs the transcripts, which are on the original machine only — rerun the harness on your project for that part. |
| before/after 14/09: US$/call −45%, ctx median 262k → 134k | SAVINGS (realised), report/usage-real-2026-09-17.md | `python tools/before_after.py --split 2026-09-14 --daily`. Sessions bucketed by the day of their first call; same `load()` and thresholds as `ledger.py`. Check it is a step: the `--daily` rows on 13/09 and 14/09. Check calls/day did not fall with it. |
| 200k cap = 33% ceiling | SAVINGS | `python tools/ledger.py --cap 200000`, line `history-cap`: Σ max(0, ctx − cap) × 0.5/M over main-thread calls. Pure arithmetic; that is why it is called a ceiling. |

## 4. Definitions that move the numbers (and by how much)

- **"Break"** = `cache_creation` > 20% of the previous call's context *and*
  > 20k tokens. Lowering to 10% adds small writes (skill loads, big tool
  results) that are legitimate growth, not breaks. The 60-min cliff is
  insensitive to the threshold; the 5–60 min band is not (it is where the
  ambiguity lives).
- **"Full re-write from the shared prefix"** (rewrites.py) additionally
  requires `cache_read` ≤ 60k: the history was intact but only the
  system+tools block was served. `ledger.py` does not apply this filter in
  its cause table, so its `unexplained` count (793) is lower than
  `rewrites.py`'s (1,059): the latter includes the hook-correlated events
  that `ledger.py` lists separately (384) and a different cr filter. Both
  scripts print their rule; pick one and be consistent.
- **Sessions with < 5 calls are excluded** everywhere (`--min-calls 5`).
  Including them adds ~70 sessions and changes shares by < 1 point.
- **Price of a 1h write** is the single biggest assumption in the write
  lines: 2× input. If your account was in overage (5m writes), `ledger.py`
  prices them at 1.25× — the bucket split is in its output, so you will see
  it.

## 5. What is *not* auditable from the logs

- Anything inside the client binary (autocompact thresholds, what
  "microcompact" prunes). Inferred from usage deltas and strings; labelled as
  such in the reports.
- Why a hook's `additionalContext` correlates with a prefix re-write. The
  instrument (`cache-proxy.py` keeps every body; `diverge.py` finds the first
  differing byte) exists; at the time of writing no break had landed while
  the proxy was up.
- Whether the 200k-cap ceiling is reachable. Only an A/B of "long session"
  vs "handoff + `/clear` every N calls" on the same work would tell. Not done.
- Subscription accounting. The rate limit counts something; the docs do not
  say it is these tokens at these weights.

## 6. If a number here disagrees with yours

That is the expected outcome; one user's shares are not another's. What
should hold: the dedup factor (~1.7×, structural), the 60-min cliff (the
TTL), the bucket split (doc'd), the price multipliers (published), the sign
of the config-vs-bare result on the prefix write (structural: `CLAUDE.md` is
not shared). If one of *those* disagrees, open an issue with the script
output — that is a finding.
