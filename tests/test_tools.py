#!/usr/bin/env python3
"""Tests for tools/*.py against synthetic transcripts (tests/fixture.py).

    python -m unittest discover -s tests -v

Stdlib only. Touches nothing under ~/.claude: every tool is run with
CLAUDE_CONFIG_DIR pointing at a temp dir.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
TOOLS = os.path.join(REPO, "tools")
sys.path.insert(0, HERE)
sys.path.insert(0, TOOLS)

import fixture  # noqa: E402


def run_tool(name, *args, cfg, env=None):
    e = {**os.environ, "CLAUDE_CONFIG_DIR": cfg, "PYTHONIOENCODING": "utf-8", **(env or {})}
    return subprocess.run([sys.executable, os.path.join(TOOLS, name), *args],
                          capture_output=True, text=True, encoding="utf-8", errors="replace", env=e)


class ToolsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="ccf-tools-")
        cls.cfg, cls.s1, cls.s2 = fixture.build(cls.tmp)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    # --- sessions.py -------------------------------------------------------

    def test_iter_calls_dedups_one_line_per_content_block(self):
        import sessions
        calls = list(sessions.iter_calls(self.s1, seen=set()))
        with open(self.s1, encoding="utf-8") as fh:
            usage_lines = sum(1 for l in fh if '"usage"' in l)
        self.assertEqual(usage_lines, 2 * len(fixture.S1_CALLS))
        self.assertEqual(len(calls), len(fixture.S1_CALLS))
        self.assertEqual(sum(c["cache_creation"] for c in calls), fixture.S1_CACHE_CREATION)

    def test_iter_calls_keeps_call_fields(self):
        import sessions
        c0 = next(sessions.iter_calls(self.s1, seen=set()))
        self.assertEqual(c0["model"], fixture.MODEL)
        self.assertEqual(c0["version"], fixture.VERSION)
        self.assertEqual(c0["cache_read"], 0)

    def test_resume_copy_counts_only_what_it_added(self):
        r = run_tool("sessions.py", "--last", "0", "--json", cfg=self.cfg)
        self.assertEqual(r.returncode, 0, r.stderr)
        rows = {json.loads(l)["session"]: json.loads(l) for l in r.stdout.splitlines() if l.strip()}
        self.assertEqual(rows["s1"]["calls"], len(fixture.S1_CALLS))
        self.assertEqual(rows["s2"]["calls"], 1)
        self.assertEqual(rows["s2"]["cache_creation"], fixture.S2_EXTRA[3])

    def test_sessions_table_shows_cold_starts_and_prompt(self):
        r = run_tool("sessions.py", "--last", "0", cfg=self.cfg)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("cold starts (cache_read=0): 1/2", r.stdout)
        self.assertIn(fixture.FIRST_PROMPT, r.stdout)

    def test_sessions_exits_nonzero_without_transcripts(self):
        empty = tempfile.mkdtemp(prefix="ccf-empty-")
        try:
            r = run_tool("sessions.py", cfg=empty)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("no transcripts", r.stderr)
        finally:
            shutil.rmtree(empty, ignore_errors=True)

    def test_cost_uses_opus_multipliers(self):
        import sessions
        c = sessions.cost({"input": 10**6, "cache_creation": 10**6, "cache_read": 10**6, "output": 10**6})
        self.assertAlmostEqual(c["input"], 5.0)
        self.assertAlmostEqual(c["cache_read"], 0.5)
        self.assertAlmostEqual(c["cache_creation"], 10.0)
        self.assertAlmostEqual(c["output"], 25.0)

    # --- breaks.py ---------------------------------------------------------

    @staticmethod
    def _call(ts, model=fixture.MODEL, cw=0, cr=0, inp=5):
        return {"ts": ts, "model": model, "input": inp, "cache_creation": cw, "cache_read": cr}

    def test_classify_each_kind(self):
        import breaks
        prev = self._call("2026-09-14T10:00:00.000Z", cw=1000, cr=200000)
        cases = {
            "ttl": (self._call("2026-09-14T11:01:00.000Z", cw=200000, cr=0), []),
            "compact": (self._call("2026-09-14T10:05:00.000Z", cw=100000, cr=60000), ["2026-09-14T10:02:00.000Z"]),
            "resume": (self._call("2026-09-14T10:05:00.000Z", model="claude-sonnet-5", cw=200000), []),
            "prune": (self._call("2026-09-14T10:05:00.000Z", cw=60000, cr=60000), []),
            "cold": (self._call("2026-09-14T10:05:00.000Z", cw=200000, cr=0), []),
            "partial": (self._call("2026-09-14T10:05:00.000Z", cw=100000, cr=110000), []),
        }
        for kind, (cur, compacts) in cases.items():
            with self.subTest(kind=kind):
                self.assertEqual(breaks.classify(prev, cur, compacts)[0], kind)

    def test_classify_synthetic_previous_is_resume(self):
        import breaks
        prev = self._call("2026-09-14T10:00:00.000Z", model="<synthetic>", cw=0, cr=200000)
        cur = self._call("2026-09-14T10:01:00.000Z", cw=200000, cr=0)
        self.assertEqual(breaks.classify(prev, cur, [])[0], "resume")

    def test_breaks_cli_finds_one_of_each_kind(self):
        r = run_tool("breaks.py", "--last", "0", "--min-calls", "1", cfg=self.cfg)
        self.assertEqual(r.returncode, 0, r.stderr)
        for kind, tokens in (("ttl", "88,000"), ("compact", "30,000"), ("resume", "60,000")):
            with self.subTest(kind=kind):
                self.assertRegex(r.stdout, r"(?m)^%s\s+1\s+%s\b" % (kind, tokens))
        self.assertNotRegex(r.stdout, r"(?m)^(prune|cold|partial)\s")
        self.assertRegex(r.stdout, r"(?m)^all\s+3\s+178,000\s+68%")

    # --- ttl.py ------------------------------------------------------------

    def test_ttl_buckets_gap_and_break_rate(self):
        r = run_tool("ttl.py", "--last", "0", "--min-calls", "1", cfg=self.cfg)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertRegex(r.stdout, r"(?m)^\s+60-90\s+1\s+1\s+100%")   # the ttl break
        self.assertRegex(r.stdout, r"(?m)^\s+2-5\s+1\s+1\s+100%")     # the compact break (2 min gap)
        self.assertRegex(r.stdout, r"(?m)^\s+0-2\s+5\s+1\s+20%")      # the resume break

    # --- rewrites.py -------------------------------------------------------

    def test_rewrites_counts_boundaries_and_unexplained(self):
        r = run_tool("rewrites.py", "--last", "0", "--min-calls", "1", cfg=self.cfg)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("boundaries 5; full re-writes from the shared prefix 1 (20.0%)", r.stdout)
        self.assertIn("re-writes with no prefix-changing event between the calls: 1 (30,000 tokens)", r.stdout)

    # --- ledger.py ---------------------------------------------------------

    def test_ledger_json_totals_match_dedup(self):
        r = run_tool("ledger.py", "--min-calls", "1", "--json", cfg=self.cfg)
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.loads(r.stdout)
        self.assertEqual(d["sessions"], 2)
        self.assertEqual(d["tokens"]["cw"], fixture.S1_CACHE_CREATION + fixture.S2_EXTRA[3])

    # --- first_call.py -----------------------------------------------------

    def test_first_call_honours_config_dir(self):
        r = run_tool("first_call.py", cfg=self.cfg)
        self.assertEqual(r.returncode, 0, r.stderr)
        rows = [l for l in r.stdout.splitlines() if "D--proj-a" in l]
        self.assertEqual(len(rows), 2, r.stdout)
        self.assertIn("cold >=60min n= 2", r.stdout)

    def test_first_call_empty_dir_exits_zero(self):
        empty = tempfile.mkdtemp(prefix="ccf-empty-")
        try:
            r = run_tool("first_call.py", cfg=empty)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertNotIn("D--proj-a", r.stdout)
        finally:
            shutil.rmtree(empty, ignore_errors=True)

    # --- _common.py --------------------------------------------------------

    def test_common_ts_parses_z_and_offset(self):
        import _common
        a = _common.ts("2026-09-14T10:00:00.000Z")
        b = _common.ts("2026-09-14T10:00:00+00:00")
        self.assertEqual(a, b)
        self.assertEqual(a.utcoffset(), timezone.utc.utcoffset(None))

    def test_every_tool_shares_one_ts(self):
        import _common, breaks, ledger, rewrites
        self.assertIs(breaks.ts, _common.ts)
        self.assertIs(ledger.ts, _common.ts)
        self.assertIs(rewrites.ts, _common.ts)

    def test_tools_survive_a_cp1252_console(self):
        """PYTHONIOENCODING=cp1252 mimics a Windows console; the fixture prompt has an 'é'."""
        cases = [("sessions.py", ["--last", "0"]), ("breaks.py", ["--last", "0", "--min-calls", "1"]),
                 ("ttl.py", ["--last", "0", "--min-calls", "1"]), ("rewrites.py", ["--last", "0", "--min-calls", "1"]),
                 ("ledger.py", ["--min-calls", "1"]), ("first_call.py", [])]
        for tool, args in cases:
            with self.subTest(tool=tool):
                r = run_tool(tool, *args, cfg=self.cfg, env={"PYTHONIOENCODING": "cp1252:strict"})
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertNotIn("UnicodeEncodeError", r.stderr)


if __name__ == "__main__":
    unittest.main()
