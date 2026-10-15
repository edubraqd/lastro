#!/usr/bin/env python3
"""Handoff lineage: with sibling sessions in one project, each /clear gets its own handoff.

Reproduces the 15/10 cascade (D:/Clientes/PTGE/PRO-EX, four desktop sessions): every /clear
and every new session took the newest handoff not loaded yet, whoever wrote it, and the
sibling that wrote it got another one on its own /clear.

    python -m unittest tests.test_handoff_lineage -v

Needs node on PATH. Touches nothing under ~/.claude.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# the session that runs the tests has its own lineage and settings env: none of it may reach the hooks
LEAK = ('CLAUDE_CODE_HOST_SESSION_ID', 'CLAUDE_PID', 'CLAUDE_PROJECT_DIR', 'CONTEXT_LANG', 'CANARY',
        'CANARY_NAME', 'HANDOFF_HOURS', 'CONTEXT_LIMIT', 'CONTEXT_HARD_LIMIT', 'EVICTION_LIMIT')


def desktop(name, pid):
    # the desktop app keeps its session id across /clear but starts a new CLI process (measured 15/10)
    return {'CLAUDE_CODE_HOST_SESSION_ID': 'local_' + name, 'CLAUDE_PID': str(pid)}


def terminal(pid):
    # a terminal /clear keeps the CLI process; the CLI sets CLAUDE_PID for its hooks (measured 15/10)
    return {'CLAUDE_PID': str(pid)}


class LineageTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='ccf-lineage-')
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.cfg = os.path.join(self.tmp, 'claude')
        os.makedirs(self.cfg)
        self.cwd = os.path.join(self.tmp, 'proj')
        self.proj = os.path.join(self.cwd, '.claude')
        os.makedirs(self.proj)
        self.tr = os.path.join(self.tmp, 'session.jsonl')
        call = {'type': 'assistant', 'message': {'id': 'msg_1', 'usage': {
            'input_tokens': 5, 'cache_creation_input_tokens': 1000, 'cache_read_input_tokens': 9000, 'output_tokens': 5}}}
        with open(self.tr, 'w', encoding='utf-8') as fh:
            fh.write(json.dumps(call) + '\n')

    def run_hook(self, hook, payload, env):
        e = {k: v for k, v in os.environ.items() if k not in LEAK}
        e.update({'CLAUDE_CONFIG_DIR': self.cfg, 'CONTEXT_LIMIT': '99999999', **env})
        r = subprocess.run(['node', os.path.join(REPO, 'hooks', hook + '.js')],
                           input=json.dumps(payload).encode('utf-8'), capture_output=True, env=e)
        self.assertEqual(r.returncode, 0, r.stderr)
        out = r.stdout.decode('utf-8')
        return json.loads(out)['hookSpecificOutput']['additionalContext'] if out.strip() else ''

    def ran_and_left_a_handoff(self, sid, env, minutes_ago):
        # the owner record comes from the guard, as in production (a prompt in that session)
        self.run_hook('context-guard', {'session_id': sid, 'transcript_path': self.tr, 'cwd': self.cwd,
                                        'hook_event_name': 'UserPromptSubmit'}, env)
        f = os.path.join(self.proj, 'handoff-' + sid[:8] + '.md')
        with open(f, 'w', encoding='utf-8') as fh:
            fh.write('# Handoff ' + sid[:8] + '\n')
        t = time.time() - minutes_ago * 60
        os.utime(f, (t, t))

    def start(self, sid, env, source='startup'):
        return self.run_hook('handoff-load', {'source': source, 'cwd': self.cwd, 'session_id': sid}, env)

    def got(self, text):
        return [l[len('# Handoff '):] for l in text.splitlines() if l.startswith('# Handoff ')]

    def peaks(self):
        with open(os.path.join(self.cfg, '.context-peaks.json'), encoding='utf-8') as fh:
            return json.load(fh)

    def test_desktop_cascade(self):
        a, b, c = 'aaaa0001' * 2, 'bbbb0002' * 2, 'cccc0003' * 2
        self.ran_and_left_a_handoff(a, desktop('a', 101), 30)   # the oldest
        self.ran_and_left_a_handoff(b, desktop('b', 102), 20)
        self.ran_and_left_a_handoff(c, desktop('c', 103), 10)   # the newest
        # a new desktop session in the same project (a card, start_session) steals nothing
        t = self.start('eeee0005' * 2, desktop('new', 105))
        self.assertEqual(self.got(t), [], 'a new session takes no sibling handoff')
        self.assertIn('handoff-cccc0003.md) but was NOT loaded', t, 'it is told the newest exists, nothing more')
        self.assertNotIn('handoff_loaded_by', json.dumps(self.peaks()), 'and nothing is marked as loaded')
        # the oldest session runs /clear: the desktop starts a new CLI process, same desktop session
        self.assertEqual(self.got(self.start('aaaa1111' * 2, desktop('a', 201))), ['aaaa0001'],
                         'the /clear of the oldest gets its own handoff, not the newest')
        self.assertEqual(self.peaks()[a]['handoff_loaded_by'], 'aaaa1111' * 2)
        self.assertEqual(self.got(self.start('cccc1111' * 2, desktop('c', 203))), ['cccc0003'])
        self.assertEqual(self.got(self.start('bbbb1111' * 2, desktop('b', 202))), ['bbbb0002'],
                         'the sibling still finds its own handoff when its turn comes')
        # the in-process /clear (source "clear") keeps the desktop session id too
        self.ran_and_left_a_handoff('aaaa1111' * 2, desktop('a', 201), 1)
        self.assertEqual(self.got(self.start('aaaa2222' * 2, desktop('a', 201), 'clear')), ['aaaa1111'])

    def test_terminal_clear_and_restart(self):
        p, q = 'dddd0004' * 2, 'ffff0006' * 2
        sleeper = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
        self.addCleanup(sleeper.kill)
        self.ran_and_left_a_handoff(p, terminal(os.getpid()), 20)   # alive: this test process
        self.ran_and_left_a_handoff(q, terminal(sleeper.pid), 10)   # alive, and newer
        self.assertEqual(self.got(self.start('dddd1111' * 2, terminal(os.getpid()), 'clear')), ['dddd0004'],
                         'a terminal /clear keeps the process: same CLAUDE_PID, own handoff')
        dead = subprocess.Popen([sys.executable, '-c', 'pass'])
        dead.wait()
        self.assertEqual(self.got(self.start('9999' * 4, terminal(dead.pid))), [],
                         'a new terminal session does not take the handoff of a sibling still running')
        sleeper.kill()
        sleeper.wait()
        self.assertEqual(self.got(self.start('8888' * 4, terminal(dead.pid))), ['ffff0006'],
                         'once that session has exited, a new one may resume its work')

    def test_handoff_from_before_the_lineage_check(self):
        # peaks written by the old hooks carry no lineage: a session that knows its own does not
        # guess, it is told the file exists (the swap backfills the handoffs still waiting)
        old = 'abab0007' * 2
        with open(os.path.join(self.cfg, '.context-peaks.json'), 'w', encoding='utf-8') as fh:
            json.dump({old: {'peak': 1, 'turns_above': 0, 'project': self.cwd}}, fh)
        with open(os.path.join(self.proj, 'handoff-abab0007.md'), 'w', encoding='utf-8') as fh:
            fh.write('# Handoff abab0007\n')
        t = self.start('abab1111' * 2, desktop('x', 301))
        self.assertEqual(self.got(t), [])
        self.assertIn('handoff-abab0007.md) but was NOT loaded', t)
        # a session without a lineage (an older CLI) keeps the old walk: the newest not loaded yet
        self.assertEqual(self.got(self.start('abab2222' * 2, {})), ['abab0007'])


if __name__ == '__main__':
    unittest.main()
