#!/usr/bin/env python3
"""End-to-end test of the hooks and the installer against a temporary CLAUDE_CONFIG_DIR.

    python -m unittest discover -s tests -v
    python tests/test_hooks.py

Needs node on PATH. Touches nothing under ~/.claude.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SID = 'abcdef1234567890'


class HooksTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix='ccf-')
        cls.cfg = os.path.join(cls.tmp, 'claude'); os.makedirs(cls.cfg)
        cls.cwd = os.path.join(cls.tmp, 'proj')
        cls.proj = os.path.join(cls.cwd, '.claude'); os.makedirs(cls.proj)
        # a synthetic transcript: two blocks of the same call (as Claude Code writes them), context 300k
        cls.big = os.path.join(cls.tmp, 'session.jsonl')
        call = {'type': 'assistant', 'requestId': 'req_1', 'timestamp': '2026-09-14T10:00:00.000Z',
                'message': {'id': 'msg_1', 'model': 'claude-opus-5',
                            'usage': {'input_tokens': 5, 'cache_creation_input_tokens': 1000, 'cache_read_input_tokens': 299000, 'output_tokens': 50}}}
        with open(cls.big, 'w', encoding='utf-8') as fh:
            fh.write(json.dumps({'type': 'user', 'message': {'content': 'hi'}}) + '\n')
            fh.write(json.dumps(call) + '\n')
            fh.write(json.dumps({**call, 'message': {**call['message'], 'usage': {'input_tokens': 0, 'cache_creation_input_tokens': 0, 'cache_read_input_tokens': 0, 'output_tokens': 0}}}) + '\n')
        cls.base = {'session_id': SID, 'transcript_path': cls.big, 'cwd': cls.cwd}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def run_hook(self, hook, payload, env=None):
        e = {**os.environ, 'CLAUDE_CONFIG_DIR': self.cfg, **(env or {})}
        r = subprocess.run(['node', os.path.join(REPO, 'hooks', hook + '.js')], input=json.dumps(payload),
                           capture_output=True, text=True, env=e, encoding='utf-8')
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout) if r.stdout.strip() else None

    def run_py(self, script, *args):
        e = {**os.environ, 'CLAUDE_CONFIG_DIR': self.cfg}
        return subprocess.run([sys.executable, os.path.join(REPO, script), *args], capture_output=True, text=True, env=e, encoding='utf-8')

    def peaks(self):
        with open(os.path.join(self.cfg, '.context-peaks.json'), encoding='utf-8') as fh:
            return json.load(fh)

    def test_context_guard(self):
        o = self.run_hook('context-guard', self.base, {'CONTEXT_LIMIT': '99999999'})
        self.assertIsNone(o, 'guard silent below limit')
        p = self.peaks()
        self.assertEqual((p[SID]['route'], p[SID]['peak']), ('direct', 300005), 'guard wrote peaks with route=direct')
        o = self.run_hook('context-guard', self.base, {'CONTEXT_LIMIT': '1000'})
        self.assertIn('SESSION CONTEXT', o['hookSpecificOutput']['additionalContext'], 'guard warns above limit (en)')
        o = self.run_hook('context-guard', self.base, {'CONTEXT_LIMIT': '1000', 'CONTEXT_LANG': 'pt'})
        self.assertIn('CONTEXTO DA SESSAO', o['hookSpecificOutput']['additionalContext'], 'guard warns above limit (pt)')
        self.run_hook('context-guard', self.base, {'CONTEXT_LIMIT': '1000', 'ANTHROPIC_BASE_URL': 'http://127.0.0.1:8790'})
        self.assertEqual(self.peaks()[SID]['route'], 'proxy', 'guard tags route=proxy from ANTHROPIC_BASE_URL')

    def test_batch_eviction(self):
        o = self.run_hook('batch-eviction', self.base, {'EVICTION_LIMIT': '1000'})
        self.assertEqual(o['decision'], 'block')
        self.assertIn('handoff-abcdef12.md', o['reason'], 'eviction blocks with handoff path')
        self.assertIsNone(self.run_hook('batch-eviction', self.base, {'EVICTION_LIMIT': '1000'}), 'eviction fires once per session')
        o3 = self.run_hook('batch-eviction', {**self.base, 'stop_hook_active': True, 'session_id': 'x' * 16}, {'EVICTION_LIMIT': '1000'})
        self.assertIsNone(o3, 'eviction ignores stop_hook_active')
        o4 = self.run_hook('batch-eviction', {**self.base, 'session_id': 'y' * 16}, {'EVICTION_LIMIT': '1000', 'CONTEXT_LANG': 'pt'})
        self.assertIn('handoff', o4['reason'])
        self.assertIn('Contexto', o4['reason'], 'eviction pt')

    def test_handoff_load(self):
        o = self.run_hook('handoff-load', {'source': 'startup', 'cwd': self.cwd})
        t = o['hookSpecificOutput']['additionalContext']
        self.assertIn('**Lastro · t<N>', t, 'canary gen1 default name')
        self.assertNotIn('gen 2', t)
        with open(os.path.join(self.proj, 'handoff-abcdef12.md'), 'w', encoding='utf-8') as fh:
            fh.write('# Handoff\n- done: X\n')
        o = self.run_hook('handoff-load', {'source': 'clear', 'cwd': self.cwd}, {'CANARY_NAME': 'Eduardo', 'CONTEXT_LANG': 'pt'})
        t = o['hookSpecificOutput']['additionalContext']
        for needle in ('HANDOFF DA SESSAO ANTERIOR', '- done: X', '(gen 2)', '**Eduardo · t<N>'):
            self.assertIn(needle, t, 'handoff-load injects handoff + gen 2 + name (pt)')
        self.assertIsNone(self.run_hook('handoff-load', {'source': 'resume', 'cwd': self.cwd}), 'silent on resume')
        o = self.run_hook('handoff-load', {'source': 'startup', 'cwd': self.cwd}, {'CANARY': '0', 'HANDOFF_HOURS': '0.0000001'})
        self.assertIsNone(o, 'silent: canary off + handoff too old')

    def test_read_recovery(self):
        f = os.path.join(self.tmp, 'file.txt')
        with open(f, 'w') as fh:
            fh.write('\n'.join(str(i) for i in range(100)) + '\n')
        o = self.run_hook('read-recovery', {'tool_name': 'Read', 'tool_input': {'file_path': f, 'limit': 10}})
        t = o['hookSpecificOutput']['additionalContext']
        self.assertIn('lines 1-10 of 100', t)
        self.assertIn('offset=11', t, 'reports remaining lines')
        self.assertIsNone(self.run_hook('read-recovery', {'tool_name': 'Read', 'tool_input': {'file_path': f, 'limit': 10, 'offset': 95}}), 'silent when exhausted')
        self.assertIsNone(self.run_hook('read-recovery', {'tool_name': 'Read', 'tool_input': {'file_path': f + '.missing', 'limit': 10}}), 'silent on missing file')
        self.assertIsNone(self.run_hook('read-recovery', {'tool_name': 'Bash', 'tool_input': {}}), 'ignores other tools')

    def test_install(self):
        settings_path = os.path.join(self.cfg, 'settings.json')
        settings = {'env': {'X': '1'}, 'hooks': {'Stop': [{'hooks': [{'type': 'command', 'command': 'node other.js'}]}]}}
        with open(settings_path, 'w', encoding='utf-8') as fh:
            json.dump(settings, fh)

        def current():
            with open(settings_path, encoding='utf-8') as fh:
                return json.load(fh)

        d = json.loads(self.run_py('hooks/install.py', '--dry-run').stdout)
        self.assertEqual(set(d['hooks']), {'UserPromptSubmit', 'Stop', 'SessionStart', 'PostToolUse'})
        self.assertEqual(len(d['hooks']['Stop']), 2, 'foreign Stop hook kept, ours added')
        self.assertEqual(d['hooks']['PostToolUse'][0]['matcher'], 'Read')
        self.assertEqual(d['env'], {'X': '1'})
        self.assertEqual(current(), settings, 'dry-run wrote nothing')
        r = self.run_py('hooks/install.py')
        self.assertIn('installed', r.stdout)
        self.assertTrue(os.path.exists(settings_path + '.bak'), 'install writes a backup')
        self.assertEqual(len(current()['hooks']['Stop']), 2)
        self.run_py('hooks/install.py')
        d = current()
        self.assertEqual((len(d['hooks']['Stop']), len(d['hooks']['SessionStart'])), (2, 1), 'install is idempotent')
        self.run_py('hooks/install.py', '--uninstall')
        self.assertEqual(current()['hooks'], {'Stop': [{'hooks': [{'type': 'command', 'command': 'node other.js'}]}]}, 'uninstall leaves only the foreign hook')
        self.run_py('hooks/install.py', '--only', 'read-recovery', '--project', self.cwd)
        with open(os.path.join(self.proj, 'settings.json'), encoding='utf-8') as fh:
            self.assertEqual(list(json.load(fh)['hooks']), ['PostToolUse'], 'install --only --project')

    def test_ab_route_reads_peaks_file(self):
        self.run_hook('context-guard', self.base, {'CONTEXT_LIMIT': '99999999', 'ANTHROPIC_BASE_URL': 'http://127.0.0.1:8790'})
        r = self.run_py('tools/ab-route.py', '--since', '2000-01-01')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('proxy', r.stdout)


if __name__ == '__main__':
    unittest.main()
