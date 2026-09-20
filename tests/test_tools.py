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
import warnings
from datetime import timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
TOOLS = os.path.join(REPO, "tools")
sys.path.insert(0, HERE)
sys.path.insert(0, TOOLS)

import fixture  # noqa: E402

S1_FIRST_CW_MEDIAN = int((fixture.S1_CALLS[0][3] + fixture.S2_EXTRA[3]) / 2)


def run_tool(name, *args, cfg, env=None):
    e = {**os.environ, "CLAUDE_CONFIG_DIR": cfg, "PYTHONIOENCODING": "utf-8", **(env or {})}
    return subprocess.run([sys.executable, os.path.join(TOOLS, name), *args],
                          capture_output=True, text=True, encoding="utf-8", errors="replace", env=e)


class ToolsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="ccf-tools-")
        cls.cfg, cls.s1, cls.s2 = fixture.build(cls.tmp)
        cls.side, cls.s3 = fixture.build_side(os.path.join(cls.tmp, "side"))

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

    def test_tied_mtime_still_puts_the_original_first(self):
        """cp / archive extraction can give both files one mtime; a copy sorted first would take every call.
        Only fails pre-fix where listdir is name-ordered (NTFS, APFS); ext4 order is hash-based."""
        tmp = tempfile.mkdtemp(prefix="ccf-tie-")
        try:
            cfg, p1, p2 = fixture.build(tmp)
            proj = os.path.dirname(p1)
            orig, copy = os.path.join(proj, "z-orig.jsonl"), os.path.join(proj, "a-copy.jsonl")
            os.rename(p1, orig)
            os.rename(p2, copy)
            for p in (orig, copy):
                os.utime(p, (1700000000, 1700000000))
            r = run_tool("sessions.py", "--last", "0", "--json", cfg=cfg)
            self.assertEqual(r.returncode, 0, r.stderr)
            rows = {json.loads(l)["session"]: json.loads(l)["calls"] for l in r.stdout.splitlines() if l.strip()}
            self.assertEqual(rows, {"z-orig": len(fixture.S1_CALLS), "a-copy": 1})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_negative_last_keeps_every_transcript(self):
        """paths[:-1] would drop the oldest file without a word; anything not positive means all."""
        r = run_tool("sessions.py", "--last", "-1", "--json", cfg=self.cfg)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual({json.loads(l)["session"] for l in r.stdout.splitlines() if l.strip()}, {"s1", "s2"})

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

    def test_sessions_names_the_filter_that_left_nothing(self):
        """Transcripts exist: the message must point at --min-calls / --project, not at the path."""
        r = run_tool("sessions.py", "--last", "0", "--min-calls", "100", cfg=self.cfg)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("no transcripts with >= 100 calls", r.stderr)
        r = run_tool("sessions.py", "--last", "0", "--project", "zzz", cfg=self.cfg)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("no transcripts under", r.stderr)
        self.assertIn("--project zzz", r.stderr)

    def test_break_rule_has_one_home(self):
        """> 20% of the previous context AND > 20k: the definition every reported number rests on."""
        import breaks, sessions, ttl
        self.assertIs(breaks.rewrote, sessions.rewrote)
        self.assertIs(ttl.rewrote, sessions.rewrote)
        self.assertIs(breaks.ctx, sessions.ctx)
        self.assertIs(ttl.ctx, sessions.ctx)
        self.assertEqual(sessions.ctx(self._call("t", cw=1000, cr=200000)), 201005)
        self.assertTrue(sessions.rewrote(20001, 100000))
        self.assertFalse(sessions.rewrote(20000, 50000))      # 40% of the context, but not > 20k: the 20k clause decides
        self.assertFalse(sessions.rewrote(30000, 150000))     # not > 20% of the previous context

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

    # --- sidechain (fixture.build_side) -----------------------------------

    def test_iter_calls_marks_sidechain(self):
        """The TTL buckets (cw5m/cw1h) are read by ledger.load, which has its own loader; nothing
        downstream of iter_calls uses them, so it does not carry them."""
        import sessions
        calls = list(sessions.iter_calls(self.s3, seen=set()))
        self.assertEqual([c["side"] for c in calls], [False] * 3 + [True] * 3 + [False])
        self.assertEqual({k for k in calls[0] if k.startswith("cw")}, set())

    def test_sidechain_calls_skip_pairwise_but_count_in_totals(self):
        """A subagent's first call is a cold start of another prefix, not a break of the main thread's."""
        r = run_tool("breaks.py", "--last", "0", "--min-calls", "1", cfg=self.side)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("sessions 1; calls 4; cache_creation total %s" % format(fixture.SIDE_CW - fixture.SIDE_SUB_CW, ","), r.stdout)
        self.assertRegex(r.stdout, r"(?m)^all\s+0\s")
        self.assertNotRegex(r.stdout, r"(?m)^resume\s")
        r = run_tool("ttl.py", "--last", "0", "--min-calls", "1", cfg=self.side)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertRegex(r.stdout, r"(?m)^\s+0-2\s+3\s+0\s+0%")   # 3 main pairs, none broke
        r = run_tool("ledger.py", "--min-calls", "1", "--json", cfg=self.side)
        d = json.loads(r.stdout)
        self.assertEqual(d["calls_main"], 4)
        self.assertEqual(d["tokens"]["cw"], fixture.SIDE_CW)
        self.assertEqual(d["buckets"], {"main:5m": 0, "main:1h": fixture.SIDE_CW - fixture.SIDE_SUB_CW,
                                        "side:5m": fixture.SIDE_SUB_CW, "side:1h": 0})
        self.assertEqual(d["ledger"]["resume-or-model-switch"].get("events", 0), 0)
        r = run_tool("sessions.py", "--last", "0", "--json", cfg=self.side)
        d = json.loads(r.stdout)
        self.assertEqual((d["calls"], d["cache_creation"]), (7, fixture.SIDE_CW))   # billed, so kept in totals

    def test_min_calls_counts_every_call_in_breaks_and_ttl_like_ledger(self):
        """--min-calls gates on ALL calls (subagent included) in ledger/rewrites/before_after; breaks and ttl
        must select the same sessions, even though their pairs are main-thread only."""
        n = len(fixture.SIDE_MAIN) + len(fixture.SIDE_SUB) + 1   # 7 calls, 4 of them main
        r = run_tool("ledger.py", "--min-calls", str(n), "--json", cfg=self.side)
        self.assertEqual(json.loads(r.stdout)["sessions"], 1)
        r = run_tool("breaks.py", "--last", "0", "--min-calls", str(n), cfg=self.side)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("sessions 1; calls 4;", r.stdout)
        r = run_tool("ttl.py", "--last", "0", "--min-calls", str(n), cfg=self.side)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertRegex(r.stdout, r"(?m)^\s+0-2\s+3\s+0\s+0%")
        r = run_tool("breaks.py", "--last", "0", "--min-calls", str(n + 1), cfg=self.side)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("no transcripts with >= %d calls" % (n + 1), r.stderr)

    # --- rewrites.py -------------------------------------------------------

    def test_rewrites_counts_boundaries_and_unexplained(self):
        r = run_tool("rewrites.py", "--last", "0", "--min-calls", "1", cfg=self.cfg)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("boundaries 5; full re-writes from the shared prefix 1 (20.0%)", r.stdout)
        self.assertIn("re-writes with no prefix-changing event between the calls: 1 (30,000 tokens)", r.stdout)

    def test_rewrites_bare_run_covers_every_transcript(self):
        """Every documented run uses --last 0; the bare run must not silently stop at 30 files."""
        r = run_tool("rewrites.py", "--help", cfg=self.cfg)
        self.assertIn("(0 = all)", r.stdout)
        tmp = tempfile.mkdtemp(prefix="ccf-many-")
        try:
            proj = os.path.join(tmp, "claude", "projects", "D--proj-d")
            os.makedirs(proj)
            for n in range(31):   # one boundary per file, pctx >= 20000
                with open(os.path.join(proj, "t%02d.jsonl" % n), "w", encoding="utf-8") as fh:
                    for i, cr in enumerate((0, 30000)):
                        fh.write(json.dumps({"type": "assistant", "requestId": "r%d" % i, "version": fixture.VERSION,
                                             "timestamp": "2026-09-14T10:0%d:00.000Z" % i,
                                             "message": {"id": "m%d-%d" % (n, i), "model": fixture.MODEL, "content": [],
                                                         "usage": {"input_tokens": 5, "cache_creation_input_tokens": 30000 - cr,
                                                                   "cache_read_input_tokens": cr, "output_tokens": 1}}}) + "\n")
            r = run_tool("rewrites.py", "--min-calls", "1", cfg=os.path.join(tmp, "claude"))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("boundaries 31;", r.stdout)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_rewrites_shares_ledger_loader_and_prefix_events(self):
        """One loader and one PREFIX_EVENTS set: the 'unexplained' bucket cannot desync between the two tools."""
        import ledger, rewrites
        self.assertIs(rewrites.load, ledger.load)
        self.assertIs(rewrites.PREFIX_EVENTS, ledger.PREFIX_EVENTS)

    # --- ledger.py ---------------------------------------------------------

    def test_ledger_json_totals_match_dedup(self):
        r = run_tool("ledger.py", "--min-calls", "1", "--json", cfg=self.cfg)
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.loads(r.stdout)
        self.assertEqual(d["sessions"], 2)
        self.assertEqual(d["tokens"]["cw"], fixture.S1_CACHE_CREATION + fixture.S2_EXTRA[3])

    def test_ledger_exits_nonzero_without_transcripts(self):
        """A message, not a StatisticsError; --json keeps printing its zero object."""
        empty = tempfile.mkdtemp(prefix="ccf-empty-")
        try:
            r = run_tool("ledger.py", cfg=empty)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("no transcripts", r.stderr)
            self.assertNotIn("Traceback", r.stderr)
            r = run_tool("ledger.py", "--json", cfg=empty)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(json.loads(r.stdout)["sessions"], 0)
        finally:
            shutil.rmtree(empty, ignore_errors=True)
        r = run_tool("ledger.py", "--min-calls", "999", cfg=self.cfg)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("no transcripts with >= 999 calls", r.stderr)

    def test_ledger_unexplained_top5_survives_a_major_version_bump(self):
        """Per-version counts share the bucket's Counter with events/tokens/usd; a 3.x client must still print."""
        tmp = tempfile.mkdtemp(prefix="ccf-v3-")
        try:
            proj = os.path.join(tmp, "claude", "projects", "D--proj-c")
            os.makedirs(proj)
            # same model, 1 min gap, no shrink, no prefix event: an unexplained full re-write
            rows = [("2026-09-14T10:00:00.000Z", 100000, 0), ("2026-09-14T10:01:00.000Z", 50000, 60000)]
            with open(os.path.join(proj, "s4.jsonl"), "w", encoding="utf-8") as fh:
                for i, (t, cw, cr) in enumerate(rows):
                    fh.write(json.dumps({"type": "assistant", "requestId": "r%d" % i, "timestamp": t, "version": "3.0.0",
                                         "message": {"id": "m%d" % i, "model": fixture.MODEL, "content": [],
                                                     "usage": {"input_tokens": 5, "cache_creation_input_tokens": cw,
                                                               "cache_read_input_tokens": cr, "output_tokens": 1}}}) + "\n")
            r = run_tool("ledger.py", "--min-calls", "1", cfg=os.path.join(tmp, "claude"))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("unexplained re-writes by version (top 5): [('3.0.0', 1)]", r.stdout)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_one_price_sheet_for_ledger_and_before_after(self):
        import before_after, ledger
        self.assertIs(before_after.prices, ledger.prices)
        P = 5.0 / 1e6
        self.assertEqual(ledger.prices(5.0), {"input": P, "cr": 0.1 * P, "cw1h": 2.0 * P, "cw5m": 1.25 * P, "out": 5.0 * P})

    # --- before_after.py ---------------------------------------------------

    def test_before_after_splits_by_first_call_day(self):
        r = run_tool("before_after.py", "--split", "2026-09-15", "--min-calls", "1", "--json", cfg=self.cfg)
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.loads(r.stdout)
        self.assertEqual(d["before"]["sessions"], 2)
        self.assertEqual(d["before"]["calls"], len(fixture.S1_CALLS) + 1)
        self.assertEqual(d["before"]["ttl_events"], 1)          # the 88 min gap in s1
        self.assertEqual(d["after"]["calls"], 0)
        r = run_tool("before_after.py", "--split", "2026-09-14", "--min-calls", "1", "--json", cfg=self.cfg)
        d = json.loads(r.stdout)
        self.assertEqual(d["before"]["calls"], 0)
        self.assertEqual(d["after"]["sessions"], 2)
        self.assertEqual(d["after"]["first_cw_median"], S1_FIRST_CW_MEDIAN)

    # --- first_call.py -----------------------------------------------------

    def test_first_call_honours_config_dir(self):
        r = run_tool("first_call.py", cfg=self.cfg)
        self.assertEqual(r.returncode, 0, r.stderr)
        rows = [l for l in r.stdout.splitlines() if "D--proj-a" in l]
        self.assertEqual(len(rows), 2, r.stdout)
        self.assertIn("cold >=60min n= 2", r.stdout)

    def test_first_call_gap_is_to_the_last_call_of_another_session(self):
        """Sessions in one project, one of them continued in a second file under the same sessionId:
        the gap is to the last call strictly before the first call, skipping the session's own calls.
        A session at the same instant is not before; a session in another project never counts."""
        tmp = tempfile.mkdtemp(prefix="ccf-gap-")
        try:
            proj = os.path.join(tmp, "claude", "projects", "D--proj-e")
            other = os.path.join(tmp, "claude", "projects", "D--proj-f")
            os.makedirs(proj)
            os.makedirs(other)
            # (file, sessionId, cache_read as a row marker, call timestamps, project dir)
            files = [("a", "aaaa", 1001, ("10:00", "10:05"), proj),
                     ("b", "bbbb", 1002, ("10:30", "10:40"), proj),
                     ("c", "cccc", 1003, ("10:35",), proj),
                     ("b-cont", "bbbb", 1004, ("11:00", "11:05"), proj),   # b resumed: its own 10:40 is not another session
                     ("d", "dddd", 1005, ("10:35",), proj),               # same instant as c: not strictly before, for either
                     ("e", "eeee", 1006, ("10:33",), other)]              # another project: never counts, in either direction
            for name, sid, cr, times, d in files:
                calls = [("2026-09-14T%s:00.000Z" % t, fixture.MODEL, 5, 1000, cr, 50) for t in times]
                with open(os.path.join(d, name + ".jsonl"), "w", encoding="utf-8") as fh:
                    for l in fixture._lines(calls, sid):
                        fh.write(json.dumps(l) + "\n")
            r = run_tool("first_call.py", cfg=os.path.join(tmp, "claude"))
            self.assertEqual(r.returncode, 0, r.stderr)
            # columns: mm-dd HH:MM project ver entry gap cr cc msg1; the marker cr names the row
            gaps = {l.split()[6]: l.split()[5] for l in r.stdout.splitlines() if "D--proj-" in l}
            self.assertEqual(gaps, {"1001": "None", "1002": "25", "1003": "5", "1004": "25", "1005": "5", "1006": "None"}, r.stdout)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_first_call_empty_dir_exits_zero(self):
        empty = tempfile.mkdtemp(prefix="ccf-empty-")
        try:
            r = run_tool("first_call.py", cfg=empty)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertNotIn("D--proj-a", r.stdout)
        finally:
            shutil.rmtree(empty, ignore_errors=True)

    # --- ab-route.py -------------------------------------------------------

    def test_ab_route_needs_peaks_then_groups_by_route(self):
        """test_hooks covers the peaks-file contract with no transcripts; this covers the rows."""
        r = run_tool("ab-route.py", cfg=self.cfg)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn(".context-peaks.json not found", r.stderr)
        peaks = os.path.join(self.cfg, ".context-peaks.json")
        with open(peaks, "w", encoding="utf-8") as fh:
            json.dump({"s1": {"route": "direct", "last": "2026-09-14T12:00:00Z"},
                       "s2": {"route": "proxy", "last": "2026-09-14T12:00:00Z"}}, fh)
        self.addCleanup(os.remove, peaks)   # the class fixture is shared; leave it as found
        r = run_tool("ab-route.py", "--since", "2026-09-01", cfg=self.cfg)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertRegex(r.stdout, r"(?m)^direct\s+1\s+%d\b" % len(fixture.S1_CALLS))
        # seen=set() per file: the resume copy s2 counts all of s1's calls plus its own
        self.assertRegex(r.stdout, r"(?m)^proxy\s+1\s+%d\b" % (len(fixture.S1_CALLS) + 1))
        r = run_tool("ab-route.py", "--since", "2026-09-15", cfg=self.cfg)   # both arms older than --since
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertRegex(r.stdout, r"(?m)^direct\s+0\s+0$")

    # --- diverge.py --------------------------------------------------------

    def test_diverge_two_bodies_reports_first_differing_element(self):
        a = {"model": "m", "tools": [{"name": "Bash"}], "system": [{"type": "text", "text": "s"}],
             "messages": [{"role": "user", "content": "hello world"}, {"role": "assistant", "content": "hi"}]}
        b = json.loads(json.dumps(a))
        b["messages"][0]["content"] = "hello there"
        c = json.loads(json.dumps(a))
        c["messages"].append({"role": "user", "content": "more"})
        paths = {}
        for name, body in (("a", a), ("b", b), ("c", c)):
            paths[name] = os.path.join(self.tmp, "body-%s.json" % name)
            with open(paths[name], "w", encoding="utf-8") as fh:
                json.dump(body, fh)
        # an unclosed handle only shows up as a warning on stderr; the exit code stays 0 either way
        r = run_tool("diverge.py", paths["a"], paths["a"], cfg=self.cfg, env={"PYTHONWARNINGS": "always::ResourceWarning"})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("bodies identical", r.stdout)
        self.assertNotIn("ResourceWarning", r.stderr, r.stderr)
        # cp1252: the excerpt prints U+2026 and U+2248; the module-level reconfigure must hold
        r = run_tool("diverge.py", paths["a"], paths["b"], cfg=self.cfg, env={"PYTHONIOENCODING": "cp1252:strict"})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("first differing element: #2 'messages[0] user'", r.stdout)
        self.assertIn("elements before it: 2 identical", r.stdout)
        r = run_tool("diverge.py", paths["a"], paths["c"], cfg=self.cfg)
        self.assertIn("identical up to element 4; then +1 elements", r.stdout)

    def test_diverge_all_survives_an_error_row(self):
        """cache-proxy.py logs a 529/400 as kind 'real' with usage {'error': ...}: no cache_read key."""
        import contextlib
        import io
        import diverge
        usage = {"input_tokens": 5, "cache_creation_input_tokens": 1000, "cache_read_input_tokens": 50000}
        rows = [{"ts": "t1", "kind": "real", "n_msgs": 3, "usage": usage, "body_sha": "aa", "model": "m"},
                {"ts": "t2", "kind": "real", "n_msgs": 3, "usage": {"error": "overloaded"}, "body_sha": "bb", "model": "m"},
                {"ts": "t3", "kind": "real", "n_msgs": 4, "usage": usage, "body_sha": "cc", "model": "m"}]
        log = os.path.join(self.tmp, "cache-proxy.log")
        with open(log, "w", encoding="utf-8") as fh:
            fh.write("".join(json.dumps(r) + "\n" for r in rows))
        bodies = os.path.join(self.tmp, "bodies")   # aa and cc saved, bb (the error) never was
        os.makedirs(bodies, exist_ok=True)
        for sha in ("aa", "cc"):
            with open(os.path.join(bodies, "x-" + sha + ".json"), "w", encoding="utf-8") as fh:
                json.dump({"model": "m", "messages": [{"role": "user", "content": "hi"}]}, fh)
        old = diverge.LOG, diverge.BODIES, sys.argv
        diverge.LOG, diverge.BODIES, sys.argv = log, bodies, ["diverge.py", "--all"]
        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf), warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                diverge.main()
        finally:
            diverge.LOG, diverge.BODIES, sys.argv = old
        self.assertIn("pair   prev ctx 51,005 -> cw 0 cr 0", buf.getvalue())
        self.assertEqual(buf.getvalue().count("body missing"), 1)   # only the aa -> bb pair
        self.assertIn("bodies identical", buf.getvalue())            # aa -> cc was compared
        self.assertEqual([str(w.message) for w in caught if w.category is ResourceWarning], [])   # the log and the bodies are closed

    # --- _common.py --------------------------------------------------------

    def test_common_ts_parses_z_and_offset(self):
        import _common
        a = _common.ts("2026-09-14T10:00:00.000Z")
        b = _common.ts("2026-09-14T10:00:00+00:00")
        self.assertEqual(a, b)
        self.assertEqual(a.utcoffset(), timezone.utc.utcoffset(None))

    def test_every_tool_shares_one_ts(self):
        import _common, breaks, ledger, rewrites, ttl
        self.assertIs(breaks.ts, _common.ts)
        self.assertIs(ledger.ts, _common.ts)
        self.assertIs(rewrites.ts, _common.ts)
        self.assertIs(ttl.ts, _common.ts)

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

    # --- handoff_dups.py / race_test.py (20/09 verification round) ---------------

    def _handoff_tree(self):
        """Three sessions in one project: two got handoff-aaaaaaaa.md (one is a duplicate),
        one got handoff-bbbbbbbb.md; each with a few API calls so the re-read cost is > 0."""
        root = os.path.join(self.tmp, "dups"); cfg = os.path.join(root, "claude")
        proj = os.path.join(cfg, "projects", "D--proj-h"); os.makedirs(proj, exist_ok=True)
        def inj(name, chars):
            return {"type": "attachment", "timestamp": "2026-09-14T10:00:00.000Z",
                    "attachment": {"type": "hook_additional_context", "hookEvent": "SessionStart",
                                   "content": ["HANDOFF DA SESSAO ANTERIOR (%s, ha 0.5 h). x\n<handoff file=\"%s\">\n%s\n</handoff>" % (name, name, "y" * chars)]}}
        for sid, name, ncalls in (("h1", "handoff-aaaaaaaa.md", 3), ("h2", "handoff-aaaaaaaa.md", 5), ("h3", "handoff-bbbbbbbb.md", 2)):
            lines = [inj(name, 350)] + fixture._lines(fixture.S1_CALLS[:ncalls], sid)
            with open(os.path.join(proj, sid + ".jsonl"), "w", encoding="utf-8") as fh:
                for l in lines:
                    fh.write(json.dumps(l, ensure_ascii=False) + "\n")
        return cfg

    def test_handoff_dups_counts_files_loaded_into_more_than_one_session(self):
        cfg = self._handoff_tree()
        r = run_tool("handoff_dups.py", "--json", cfg=cfg)
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.loads(r.stdout)
        self.assertEqual((d["injections"], d["files"], d["files_in_2_or_more"], d["extra_injections"]), (3, 2, 1, 1))
        self.assertEqual(d["top"][0]["file"], "handoff-aaaaaaaa.md")
        self.assertEqual(d["top"][0]["sessions"], 2)
        # the duplicate rode in h2 (5 calls): chars/3.5 tokens x 5 calls re-read, once written
        self.assertAlmostEqual(d["extra_reread_tokens"], d["top"][0]["chars"] / 3.5 * 5, delta=1)
        self.assertGreater(d["extra_usd"], 0)
        self.assertNotIn("yyyy", r.stdout, "aggregates only: no transcript text")
        r = run_tool("handoff_dups.py", cfg=cfg)
        self.assertIn("handoff-aaaaaaaa.md", r.stdout)
        self.assertIn("x2", r.stdout)

    def test_handoff_dups_exits_nonzero_without_injections(self):
        r = run_tool("handoff_dups.py", cfg=self.cfg)   # the plain fixture has no hook lines
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("no handoff injection", r.stderr)

    def test_race_test_loads_each_handoff_into_exactly_one_session(self):
        # the sandbox race that found the missing lock: with the lock, "delivered" is 1 per file
        r = run_tool("race_test.py", "--n", "8", "--files", "2", "--rounds", "2", "--json", cfg=os.path.join(self.tmp, "race-home"))
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.loads(r.stdout)
        self.assertEqual(len(d["rounds"]), 2)
        for rnd in d["rounds"]:
            self.assertEqual(rnd["delivered_max"], 1, rnd)
            self.assertEqual(rnd["marked"], 2, "every delivered file is marked in the sandbox peaks")
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "race-home", "race_proj")), "sandbox removed")


if __name__ == "__main__":
    unittest.main()
