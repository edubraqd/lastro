#!/usr/bin/env python3
"""Subagent transcripts (<session>/subagents/**/agent-*.jsonl) in ledger.py and sessions.py.

    python -m unittest tests.test_ledger_subagents -v
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import fixture  # noqa: E402
from test_tools import run_tool  # noqa: E402

# US$/M input by family; 5m write 1.25x, 1h write 2x, read 0.1x, output 5x
P = {fixture.MODEL: 5.0, "claude-sonnet-5": 3.0, "claude-haiku-4-5-20251001": 1.0}


def usd(calls, side, flat=None):
    tot = 0.0
    for (_, model, inp, cw, cr, out) in calls:
        p = (flat or P[model]) / 1e6
        tot += inp * p + cw * (1.25 if side else 2.0) * p + cr * 0.1 * p + out * 5 * p
    return tot


MAIN = fixture.SUBA_MAIN + [fixture.SUBA_LATE]
SIDE = fixture.SUBA_A1 + fixture.SUBA_A2


class LedgerSubagentsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="ccf-sub-")
        cls.cfg, cls.s4 = fixture.build_subagents(cls.tmp)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def ledger(self, *args):
        r = run_tool("ledger.py", "--min-calls", "1", "--json", *args, cfg=self.cfg)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_subagent_files_belong_to_their_session(self):
        import sessions
        found = [os.path.basename(p) for p in sessions.subagent_files(self.s4)]
        self.assertEqual(sorted(found), ["agent-a1.jsonl", "agent-a2.jsonl"])   # not journal, not meta

    def test_ledger_counts_subagents_as_side_of_the_parent(self):
        d = self.ledger()
        self.assertEqual(d["sessions"], 1)
        self.assertEqual(d["calls_main"], len(MAIN))
        self.assertEqual(d["calls_side"], len(SIDE))
        self.assertEqual(d["tokens"]["cw"], sum(c[3] for c in MAIN + SIDE))
        self.assertEqual(d["buckets"]["side:5m"], fixture.SUBA_SIDE_CW)

    def test_ledger_prices_each_call_by_its_model_and_bucket(self):
        d = self.ledger()
        self.assertAlmostEqual(d["usd_main"], usd(MAIN, side=False), places=9)
        self.assertAlmostEqual(d["usd_side"], usd(SIDE, side=True), places=9)
        self.assertAlmostEqual(d["total_usd"], usd(MAIN, False) + usd(SIDE, True), places=9)
        self.assertAlmostEqual(d["usd_by_model"]["claude-haiku-4-5-20251001"], usd(fixture.SUBA_A2, True), places=9)

    def test_price_input_is_a_flat_override(self):
        d = self.ledger("--price-input", "5")
        self.assertAlmostEqual(d["total_usd"], usd(MAIN, False, flat=5) + usd(SIDE, True, flat=5), places=9)

    def test_five_minute_writes_cost_1_25x_not_2x(self):
        cfg = fixture.build_side(os.path.join(self.tmp, "side"))[0]
        r = run_tool("ledger.py", "--min-calls", "1", "--json", "--price-input", "5", cfg=cfg)
        d = json.loads(r.stdout)
        main = fixture.SIDE_MAIN + [fixture.SIDE_BACK]
        self.assertAlmostEqual(d["usd"]["cache_creation"],
                               (sum(c[3] for c in main) * 2.0 + fixture.SIDE_SUB_CW * 1.25) * 5 / 1e6, places=9)

    def test_no_subagents_reproduces_the_old_count(self):
        d = self.ledger("--no-subagents")
        self.assertEqual(d["calls_side"], 0)
        self.assertEqual(d["tokens"]["cw"], sum(c[3] for c in MAIN))
        self.assertAlmostEqual(d["total_usd"], usd(MAIN, False), places=9)
        # --min-calls gates on every call: 4 main calls alone do not reach 5, 4 + 3 subagent calls do
        r = run_tool("ledger.py", "--json", "--no-subagents", cfg=self.cfg)
        self.assertEqual(json.loads(r.stdout)["sessions"], 0)
        r = run_tool("ledger.py", "--json", cfg=self.cfg)
        self.assertEqual(json.loads(r.stdout)["sessions"], 1)

    def test_until_drops_later_calls(self):
        d = self.ledger("--until", "2026-09-15")
        self.assertEqual(d["calls_main"], len(fixture.SUBA_MAIN))
        self.assertEqual(d["tokens"]["cw"], sum(c[3] for c in fixture.SUBA_MAIN + SIDE))

    def test_text_output_splits_main_and_subagents(self):
        r = run_tool("ledger.py", "--min-calls", "1", cfg=self.cfg)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertRegex(r.stdout, r"(?m)^\s+main thread\s+\$\s*[\d,.]+")
        self.assertRegex(r.stdout, r"(?m)^\s+subagents\s+\$\s*[\d,.]+")
        self.assertIn("claude-haiku-4-5-20251001", r.stdout)

    def test_sessions_attributes_subagent_calls_to_the_parent(self):
        r = run_tool("sessions.py", "--last", "0", "--json", cfg=self.cfg)
        self.assertEqual(r.returncode, 0, r.stderr)
        rows = [json.loads(l) for l in r.stdout.splitlines() if l.strip()]
        self.assertEqual([(x["session"], x["calls"]) for x in rows], [("s4", len(MAIN) + len(SIDE))])
        self.assertEqual(rows[0]["cache_creation"], sum(c[3] for c in MAIN + SIDE))
        r = run_tool("sessions.py", "--last", "0", "--json", "--no-subagents", cfg=self.cfg)
        self.assertEqual(json.loads(r.stdout)["calls"], len(MAIN))


if __name__ == "__main__":
    unittest.main()
