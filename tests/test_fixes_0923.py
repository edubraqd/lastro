#!/usr/bin/env python3
"""Tests for the 23/09 fixes to tools/handoff_dups.py and tools/race_test.py.

    python -m unittest discover -s tests -v

Stdlib only. Touches nothing under ~/.claude.
"""
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(os.path.dirname(HERE), "tools")
sys.path.insert(0, HERE)

import fixture  # noqa: E402


def run_tool(name, *args, env):
    return subprocess.run([sys.executable, os.path.join(TOOLS, name), *args],
                          capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)


def inj(uuid, ts, name, hours, body):
    return {"type": "attachment", "uuid": uuid, "timestamp": ts,
            "attachment": {"type": "hook_additional_context", "hookEvent": "SessionStart",
                           "content": ["HANDOFF DA SESSAO ANTERIOR (%s, ha %s h). x\n<handoff file=\"%s\">\n%s\n</handoff>" % (name, hours, name, body)]}}


class HandoffDupsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="ccf-0923-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.cfg = os.path.join(self.tmp, "claude")
        proj = os.path.join(self.cfg, "projects", "D--proj-d")
        os.makedirs(proj)
        name = "handoff-aaaaaaaa.md"
        first = inj("u-1", "2026-09-10T10:00:00.000Z", name, "0.5", "y" * 300)
        sessions = (
            # the load itself
            ("d1", [first], 3),
            # the same line copied into a resumed/forked transcript: one load, not two
            ("d1-fork", [first], 4),
            # the same body loaded again by another session (the age in the header differs): a real duplicate
            ("d2", [inj("u-2", "2026-09-14T10:00:00.000Z", name, "3.0", "y" * 300)], 5),
            # the file was rewritten and loaded: a new handoff under the same name, not a duplicate
            ("d3", [inj("u-3", "2026-09-15T10:00:00.000Z", name, "0.2", "z" * 300)], 2),
        )
        for sid, head, ncalls in sessions:
            with open(os.path.join(proj, sid + ".jsonl"), "w", encoding="utf-8") as fh:
                for l in head + fixture._lines(fixture.S1_CALLS[:ncalls], sid):
                    fh.write(json.dumps(l) + "\n")
        self.env = {**os.environ, "CLAUDE_CONFIG_DIR": self.cfg, "PYTHONIOENCODING": "utf-8"}

    def test_a_copied_line_is_one_load_and_a_rewrite_is_not_a_duplicate(self):
        r = run_tool("handoff_dups.py", "--json", env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.loads(r.stdout)
        self.assertEqual(d["injections"], 3, "the forked copy of u-1 is not a second injection")
        self.assertEqual((d["files"], d["files_in_2_or_more"], d["extra_injections"]), (1, 1, 1))
        self.assertEqual(d["top"][0]["sessions"], 2, "d1 + d2 carried the same body; d3 carried a rewrite")
        self.assertAlmostEqual(d["extra_reread_tokens"], d["top"][0]["chars"] / 3.5 * 5, delta=1, msg="the extra rode in d2 (5 calls)")

    def test_since_counts_only_loads_from_that_day_on(self):
        r = run_tool("handoff_dups.py", "--json", "--since", "2026-09-12", env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.loads(r.stdout)
        self.assertEqual(d["injections"], 2, "d2 and d3 are on/after 12/09")
        self.assertEqual(d["extra_injections"], 1, "d2 is still an extra: the first load (d1, 10/09) predates the window")
        r = run_tool("handoff_dups.py", "--json", "--since", "2026-09-20", env=self.env)
        self.assertNotEqual(r.returncode, 0, "nothing on/after 20/09")
        r = run_tool("handoff_dups.py", "--since", "12/09/2026", env=self.env)
        self.assertEqual(r.returncode, 2, "a malformed date is an argparse error")


class RaceTestCleanupTest(unittest.TestCase):
    def test_the_temp_sandbox_it_created_is_removed(self):
        tmp = tempfile.mkdtemp(prefix="ccf-0923-tmp-")
        self.addCleanup(shutil.rmtree, tmp, True)
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_CONFIG_DIR"}
        env.update(TMPDIR=tmp, TEMP=tmp, TMP=tmp, PYTHONIOENCODING="utf-8")
        r = run_tool("race_test.py", "--n", "4", "--files", "1", "--rounds", "1", "--json", env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(glob.glob(os.path.join(tmp, "ccf-race-*")), [], "mkdtemp sandbox left behind")

    def test_a_given_config_dir_is_kept(self):
        tmp = tempfile.mkdtemp(prefix="ccf-0923-cfg-")
        self.addCleanup(shutil.rmtree, tmp, True)
        env = {**os.environ, "CLAUDE_CONFIG_DIR": tmp, "PYTHONIOENCODING": "utf-8"}
        r = run_tool("race_test.py", "--n", "4", "--files", "1", "--rounds", "1", "--json", env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(os.path.isdir(tmp), "a dir the caller named is not the script's to delete")


if __name__ == "__main__":
    unittest.main()
