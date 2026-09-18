# Real usage, before and after: did any of this move the bill?

Everything in [SAVINGS.md](../SAVINGS.md) is a ceiling, a counterfactual or a
controlled A/B on one task. This is the other kind of number: the same
machine, the same person, four working days after the whole package was
installed on 2026-09-14, against the fourteen days before. Measured on
2026-09-17 with `python tools/before_after.py --split 2026-09-14 --daily`.

**What was installed on 14/09**, all at once: the context hooks in
[hooks/](../hooks/) (`context-guard` at 200k, `batch-eviction` at 150k —
it blocks the turn once and makes the model write a handoff; `handoff-load`
with the canary; `read-recovery`), `skillOverrides` on the main project,
terse-output prompting (caveman, pt-BR), and the habit the hooks enforce:
handoff + `/clear` instead of letting a session grow. A tool-output
compression proxy (`caveman wrap`) was also set up for an A/B; see the end.

## The numbers

Dedup by `(message.id, requestId)`, sessions with ≥ 5 calls, all
`claude-desktop`, API-equivalent US$ at Opus list prices (input 5, cache
read 0.5, 1h write 10, output 25 per M). Days are UTC. `ctx` = tokens
re-sent per main-thread call (input + cache write + cache read).

| period | days | sessions | calls | US$/day | US$/call | ctx median | ctx p90 | calls > 200k | TTL re-writes | TTL US$ | 1st cache write | output/call | autocompact |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| before, 31/08–13/09 | 14 | 210 | 27,798 | 446 | 0.225 | 262k | 595k | 64% | 157 | 546 | 33k | 1,014 | 17 |
| after, 14/09–18/09 | 5 | 152 | 7,656 | 188 | 0.123 | 134k | 210k | 13% | 37 | 45 | 32k | 774 | 0 |
| **delta** | | | | **−58%** | **−45%** | **−49%** | **−65%** | | | | −4% | −24% | |

Cost split moved from cache read 68% / write 20% / output 11% to
58% / 27% / 16%. Calls per session: median 91 → 47.

Per day, the two weeks around the split (the full table is what the tool
prints):

| day | sessions | calls | US$/day | US$/call | ctx median | ctx p90 | > 200k | TTL US$ |
|---|---|---|---|---|---|---|---|---|
| 09-10 | 20 | 3,362 | 763 | 0.227 | 299k | 597k | 71% | 58 |
| 09-11 | 12 | 1,265 | 243 | 0.192 | 238k | 500k | 58% | 14 |
| 09-12 | 17 | 2,066 | 405 | 0.196 | 234k | 498k | 56% | 51 |
| 09-13 | 16 | 1,749 | 306 | 0.175 | 201k | 416k | 50% | 17 |
| **09-14** | 30 | 1,595 | 205 | **0.129** | **137k** | **204k** | **12%** | 21 |
| 09-15 | 51 | 1,965 | 238 | 0.121 | 130k | 195k | 8% | 10 |
| 09-16 | 30 | 1,777 | 215 | 0.121 | 140k | 228k | 18% | 5 |
| 09-17 | 39 | 2,226 | 271 | 0.122 | 133k | 235k | 15% | 9 |

## How to read it

**It is a step, not a drift.** 13/09: context median 201k, half the calls
above 200k. 14/09: 137k and 12%. Every day since sits at 130–140k / 8–18%,
and p90 sits on the cap (195–235k). Calls per day did not fall (1.6–2.2k
after vs 1.0–3.4k before), so the −45% per call is not "worked less".
Sessions per day doubled (16 → 30–51) and calls per session halved; that
is the mechanism, not a side effect.

**What each lever contributed**, in the order the ledger predicted:

1. **The cap + handoff** is nearly all of it. The ledger called the 200k cap
   a 33% *ceiling* and refused to forecast it. Realised it came out larger,
   because two other lines shrink with it: a TTL re-write of a 130k context
   costs less than one of a 300k context (TTL US$/day 39 → 9), and
   autocompact went from 17 events in 14 days to **zero** — `/clear` replaced
   it. The price of the habit is in the number already: 152 new sessions ×
   ~32k prefix write × US$10/M ≈ US$49 over five days, ~US$10/day, against
   ~US$260/day saved.
2. **`skillOverrides`**: first-call cache write 33k → 32k. Matches the A/B
   (−2.7k tokens). Noise on the total, as SAVINGS.md said.
3. **Terse output**: output per call −24%. Confounded: a shorter context
   also means less thinking per call. The controlled number is −8%
   (findings §7); the rest is context. Output is 16% of the bill now, so
   even the full −24% is under 4% of cost.
4. **The compression proxy** (`caveman wrap claude`): **0 of 120 sessions**
   went through it (`~/.claude/.contexto-picos.json`, `rota` field). The
   A/B that was to close on 21/09 never started. Nothing here is from it.

## What this does not show

- **Quality.** 92 of 121 sessions since 14/09 ended in a forced handoff; 36
  crossed the limit at least once. If a task that used to close in one
  session now takes two, the extra session's cost is already in the
  US$/day above — the friction is not. The only quality number in this repo
  is the one-task A/B ([ab-config-vs-bare.md](ab-config-vs-bare.md): 100%
  vs 92%), and it does not test long tasks split across sessions.
- **Same work.** Before and after are different weeks of a freelancer's
  life. The step on the split day and the flat calls/day are the evidence
  that the change, not the work, moved the number; they are not an A/B.
- **Subscription.** These are quota-equivalent dollars. What was saved is
  headroom before the rate limit.

## Reproduce

```bash
python tools/before_after.py --split 2026-09-14            # 14 days each side
python tools/before_after.py --split 2026-09-14 --daily    # plus one row per day
python tools/before_after.py --split 2026-09-14 --json
```

Same `load()` and thresholds as `ledger.py` (TTL: gap > 60 min, cache write
> 20% of the previous context and > 20k; compact: history shrank below 70%
of a context over 100k). Change `--cap` and the `> cap` column moves; nothing
else does.
