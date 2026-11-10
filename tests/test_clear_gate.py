#!/usr/bin/env python3
"""Zelador: the clear gate, the arming hook, the mission texts of the other hooks, and missao.py.

A mission the user armed in a desktop session keeps going across clear_session("self"): the
gate files the request the watcher answers. Without an armed mission nothing changes.

    python -m unittest tests.test_clear_gate -v

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
LEAK = ('CLAUDE_CODE_HOST_SESSION_ID', 'CLAUDE_PID', 'CLAUDE_PROJECT_DIR', 'CONTEXT_LANG', 'CANARY',
        'CANARY_NAME', 'HANDOFF_HOURS', 'CONTEXT_LIMIT', 'CONTEXT_HARD_LIMIT', 'EVICTION_LIMIT')
HOST = 'local_a'
SID = 'a1a1a1a1' * 2
TOOL = 'mcp__ccd_session_mgmt__clear_session'


class GateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='ccf-gate-')
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.cfg = os.path.join(self.tmp, 'claude')
        self.z = os.path.join(self.cfg, 'zelador')
        os.makedirs(os.path.join(self.z, 'missoes'))
        self.cwd = os.path.join(self.tmp, 'proj')
        os.makedirs(os.path.join(self.cwd, '.claude'))
        self.tr = os.path.join(self.tmp, SID + '.jsonl')
        call = {'type': 'assistant', 'message': {'id': 'msg_1', 'usage': {
            'input_tokens': 5, 'cache_creation_input_tokens': 1000, 'cache_read_input_tokens': 9000, 'output_tokens': 5}}}
        with open(self.tr, 'w', encoding='utf-8') as fh:
            fh.write(json.dumps(call) + '\n')
        self.env = {'CLAUDE_CODE_HOST_SESSION_ID': HOST, 'CLAUDE_PID': '4242'}

    def run_hook(self, hook, payload, env=None):
        e = {k: v for k, v in os.environ.items() if k not in LEAK}
        e.update({'CLAUDE_CONFIG_DIR': self.cfg, **self.env, **(env or {})})
        r = subprocess.run(['node', os.path.join(REPO, 'hooks', hook + '.js')],
                           input=json.dumps(payload).encode('utf-8'), capture_output=True, env=e)
        self.assertEqual(r.returncode, 0, r.stderr)
        out = r.stdout.decode('utf-8')
        return json.loads(out) if out.strip() else {}

    def gate(self, target='self', env=None):
        o = self.run_hook('clear-gate', {'session_id': SID, 'transcript_path': self.tr, 'cwd': self.cwd,
                                         'hook_event_name': 'PreToolUse', 'tool_name': TOOL,
                                         'tool_input': {'session_id': target}}, env).get('hookSpecificOutput', {})
        return o.get('permissionDecision'), o.get('permissionDecisionReason', '')

    def arm(self, **over):
        m = {'host': HOST, 'estado': 'armada', 'texto': 'ship the thing', 'ciclos': 0, 'max_ciclos': 3, 'min_ctx': 0}
        m.update(over)
        with open(os.path.join(self.z, 'missoes', HOST + '.json'), 'w', encoding='utf-8') as fh:
            json.dump(m, fh)

    def mission(self):
        with open(os.path.join(self.z, 'missoes', HOST + '.json'), encoding='utf-8') as fh:
            return json.load(fh)

    def keeper(self, pid=None, cli=None):
        with open(os.path.join(self.z, 'vivo.json'), 'w', encoding='utf-8') as fh:
            json.dump({'pid': pid or os.getpid(), 'cli': cli, 'desde': 'x'}, fh)

    def start(self):
        return self.run_hook('handoff-load', {'source': 'startup', 'cwd': self.cwd, 'session_id': SID,
                                              'transcript_path': self.tr}).get('hookSpecificOutput', {}).get('additionalContext', '')

    def handoff(self, minutes_ago=0):
        f = os.path.join(self.cwd, '.claude', 'handoff-' + SID[:8] + '.md')
        with open(f, 'w', encoding='utf-8') as fh:
            fh.write('# Handoff\n')
        t = time.time() - minutes_ago * 60
        os.utime(f, (t, t))
        return f

    def request(self):
        try:
            with open(os.path.join(self.z, 'pedidos', HOST + '.json'), encoding='utf-8') as fh:
                return json.load(fh)
        except FileNotFoundError:
            return None

    def test_no_mission_no_decision(self):
        self.keeper()
        self.start()
        self.handoff()
        self.assertEqual(self.gate(), (None, ''), 'a session without a mission: the normal flow, untouched')
        self.arm(estado='concluida')
        self.assertEqual(self.gate(), (None, ''), 'a finished mission is no mission')
        self.arm()
        self.assertEqual(self.gate(target='local_other'), (None, ''), 'another session is never the gate\'s call')
        self.assertEqual(self.gate(env={'CLAUDE_CODE_HOST_SESSION_ID': ''}), (None, ''), 'a terminal has no keeper')
        self.assertIsNone(self.request())

    def test_denies_until_the_cycle_is_safe(self):
        self.arm()
        self.start()
        self.handoff()
        d, why = self.gate()
        self.assertEqual(d, 'deny')
        self.assertIn('no keeper watcher is alive', why)
        dead = subprocess.Popen([sys.executable, '-c', 'pass'])
        dead.wait()
        self.keeper(dead.pid)
        self.assertEqual(self.gate()[0], 'deny', 'a watcher that exited is no watcher')
        self.keeper(cli=dead.pid)
        d, why = self.gate()
        self.assertEqual(d, 'deny')
        self.assertIn('no keeper watcher is alive', why, 'a watcher whose keeper CLI is gone wakes nobody')
        self.keeper()
        os.remove(self.handoff())
        d, why = self.gate()
        self.assertEqual(d, 'deny')
        self.assertIn('wrote no handoff', why)
        self.handoff(minutes_ago=10)
        self.assertEqual(self.gate()[0], 'deny', 'a handoff older than this generation is not its handoff')
        self.handoff()
        self.arm(min_ctx=150000)
        d, why = self.gate()
        self.assertEqual(d, 'deny')
        self.assertIn('below the 150k minimum', why, 'the transcript is at 10k')
        self.arm(ciclos=3)
        d, why = self.gate()
        self.assertEqual(d, 'deny')
        self.assertIn('limit of 3', why)
        self.assertIsNone(self.request(), 'a denied clear files nothing')

    def test_allows_files_the_request_and_counts_once(self):
        self.arm()
        self.keeper()
        self.start()
        f = self.handoff()
        self.assertEqual(self.gate()[0], 'allow')
        r = self.request()
        self.assertEqual((r['host'], r['pid'], r['sid'], r['ciclo']), (HOST, 4242, SID, 1))
        self.assertEqual(os.path.normcase(r['handoff']), os.path.normcase(f))
        self.assertEqual(self.mission()['ciclos'], 1)
        # the Stop hook may send the model back to the handoff: a second call counts nothing
        self.assertEqual(self.gate()[0], 'allow')
        self.assertEqual((self.request()['ciclo'], self.mission()['ciclos']), (1, 1))
        # without the CLI's pid there is nothing for the watcher to wait on: normal flow
        os.remove(os.path.join(self.z, 'pedidos', HOST + '.json'))
        self.assertEqual(self.gate(env={'CLAUDE_PID': ''}), (None, ''))

    def test_the_other_hooks_speak_of_the_cycle_only_with_a_mission(self):
        big = {'EVICTION_LIMIT': '5000', 'CONTEXT_LIMIT': '5000'}
        stop = {'session_id': SID, 'transcript_path': self.tr, 'cwd': self.cwd, 'hook_event_name': 'Stop'}
        post = dict(stop, hook_event_name='PostToolUse')
        guard = lambda: self.run_hook('context-guard', post, big)['hookSpecificOutput']['additionalContext']
        self.assertNotIn('<mission>', self.start())
        self.assertNotIn('MISSION ARMED', guard())
        self.arm()
        t = self.start()
        self.assertIn('<mission>\nship the thing\n</mission>', t, 'every generation starts from the user\'s words')
        self.assertIn('zelador/missao.py" concluir', t)
        self.assertNotIn('MISSION ARMED', self.run_hook('context-guard', dict(post, session_id='b' * 16), big)
                         ['hookSpecificOutput']['additionalContext'], 'no watcher: the user still clears by hand')
        self.keeper()
        self.assertIn('MISSION ARMED', self.run_hook('context-guard', dict(post, session_id='c' * 16), big)
                      ['hookSpecificOutput']['additionalContext'])
        # the Stop hook asks for handoff + self-clear, and says nothing once the request is filed
        self.handoff()
        self.assertEqual(self.gate()[0], 'allow')
        self.assertEqual(self.run_hook('batch-eviction', stop, big), {}, 'handoff written and clear queued')
        os.remove(os.path.join(self.z, 'pedidos', HOST + '.json'))
        self.assertIn('call clear_session', self.run_hook('batch-eviction', stop, big)['reason'])
        os.remove(os.path.join(self.z, 'vivo.json'))
        self.assertIn('/clear', self.run_hook('batch-eviction', dict(stop, session_id='d' * 16), big)['reason'])

    def expand(self, args, name='missao', env=None):
        o = self.run_hook('mission-arm', {'session_id': SID, 'transcript_path': self.tr, 'cwd': self.cwd,
                                          'hook_event_name': 'UserPromptExpansion', 'expansion_type': 'slash_command',
                                          'command_name': name, 'command_args': args, 'command_source': 'userSettings',
                                          'prompt': '/%s %s' % (name, args)}, env)
        return o.get('hookSpecificOutput', {}).get('additionalContext', '')

    def test_mission_arm_hook(self):
        file = os.path.join(self.z, 'missoes', HOST + '.json')
        text = 'missão: café\n\nlinha 3 com "aspas", $VAR, 100% e <mission>'
        self.assertEqual(self.expand(text, name='zelador'), '', 'another command is not its call')
        self.assertEqual(self.expand(text, env={'CLAUDE_CODE_HOST_SESSION_ID': ''}), '', 'a terminal has no keeper')
        self.assertEqual(self.expand(' \n '), '', '/missao with no text arms nothing')
        os.mkdir(file)   # missao.py cannot write over a directory
        self.assertEqual(self.expand(text), '', 'arming failed: silent, the command arms as it did before the hook')
        os.rmdir(file)
        self.assertFalse(os.path.exists(file))
        t = self.expand('  ' + text + '\n', env={'CLAUDE_PROJECT_DIR': self.cwd})
        m = self.mission()
        self.assertEqual((m['host'], m['estado'], m['texto'], m['ciclos'], m['max_ciclos'], m['min_ctx']),
                         (HOST, 'armada', text, 0, 10, 150000), 'the user\'s words, verbatim, in missao.py\'s own scheme')
        self.assertEqual(os.path.normcase(os.path.realpath(m['projeto'])), os.path.normcase(os.path.realpath(self.cwd)))
        self.assertIn('the hook has already armed this mission', t)
        self.assertIn(file.replace('\\', '/'), t.replace('\\', '/'))
        self.assertIn('No keeper watcher is alive', t, 'armed without a keeper: the user is told')
        self.keeper()
        self.arm(ciclos=2)
        t = self.expand('second mission')
        self.assertIn('the hook has already armed this mission', t)
        self.assertNotIn('No keeper watcher', t)
        m = self.mission()
        self.assertEqual((m['texto'], m['ciclos']), ('second mission', 0), 'a new /missao replaces the old mission')
        # what it armed is what every later generation starts from
        self.assertIn('<mission>\nsecond mission\n</mission>', self.start())

    def test_missao_cli(self):
        e = {k: v for k, v in os.environ.items() if k not in LEAK}
        e.update({'CLAUDE_CONFIG_DIR': self.cfg, 'CLAUDE_CODE_HOST_SESSION_ID': HOST, 'PYTHONIOENCODING': 'utf-8'})
        cli = [sys.executable, os.path.join(REPO, 'zelador', 'missao.py')]
        run = lambda *a, **k: subprocess.run(cli + list(a), capture_output=True, env=e, **k)
        self.assertNotEqual(run('armar', input=b'  ').returncode, 0, 'an empty mission is refused')
        r = run('armar', '--max-ciclos', '4', input='missão: café'.encode('utf-8'))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('nenhum vigia vivo', r.stdout.decode('utf-8'))
        m = self.mission()
        self.assertEqual((m['estado'], m['texto'], m['ciclos'], m['max_ciclos'], m['min_ctx']),
                         ('armada', 'missão: café', 0, 4, 150000))
        self.keeper()
        st = json.loads(run('status').stdout.decode('utf-8').splitlines()[0])
        self.assertEqual((st['estado'], st['vigia_vivo']), ('armada', True))
        gone = subprocess.Popen([sys.executable, '-c', 'pass'])
        gone.wait()
        self.keeper(cli=gone.pid)
        self.assertFalse(json.loads(run('status').stdout.decode('utf-8').splitlines()[0])['vigia_vivo'],
                         'a watcher whose keeper CLI is gone wakes nobody')
        self.keeper()
        self.assertEqual(run('concluir').returncode, 0)
        self.assertEqual(self.mission()['estado'], 'concluida')
        e['CLAUDE_CODE_HOST_SESSION_ID'] = '../x'
        self.assertNotEqual(run('status').returncode, 0, 'the host names a file: only local_... passes')


if __name__ == '__main__':
    unittest.main()
