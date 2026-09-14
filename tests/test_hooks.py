#!/usr/bin/env python3
"""End-to-end test of the hooks and the installer against a temporary CLAUDE_CONFIG_DIR.

    python tests/test_hooks.py

Needs node on PATH. Touches nothing under ~/.claude.
"""
import json, os, subprocess, sys, tempfile, glob, shutil, time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tmp = tempfile.mkdtemp(prefix='ccf-')
cfg = os.path.join(tmp, 'claude'); os.makedirs(cfg)
proj = os.path.join(tmp, 'proj', '.claude'); os.makedirs(proj)

# a synthetic transcript: two blocks of the same call (as Claude Code writes them), context 300k
big = os.path.join(tmp, 'session.jsonl')
call = {'type': 'assistant', 'requestId': 'req_1', 'timestamp': '2026-09-14T10:00:00.000Z',
        'message': {'id': 'msg_1', 'model': 'claude-opus-5', 'usage': {'input_tokens': 5, 'cache_creation_input_tokens': 1000, 'cache_read_input_tokens': 299000, 'output_tokens': 50}}}
with open(big, 'w', encoding='utf-8') as fh:
    fh.write(json.dumps({'type': 'user', 'message': {'content': 'hi'}}) + chr(10))
    fh.write(json.dumps(call) + chr(10))
    fh.write(json.dumps({**call, 'message': {**call['message'], 'usage': {'input_tokens': 0, 'cache_creation_input_tokens': 0, 'cache_read_input_tokens': 0, 'output_tokens': 0}}}) + chr(10))

def run(hook, payload, env=None):
    e = {**os.environ, 'CLAUDE_CONFIG_DIR': cfg, **(env or {})}
    r = subprocess.run(['node', f'{REPO}/hooks/{hook}.js'], input=json.dumps(payload), capture_output=True, text=True, env=e, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout) if r.stdout.strip() else None

fails = 0
def check(name, cond):
    global fails
    print(('ok  ' if cond else 'FAIL'), name)
    if not cond: fails += 1

sid = 'abcdef1234567890'
base = {'session_id': sid, 'transcript_path': big, 'cwd': os.path.join(tmp, 'proj')}

# context-guard: below limit -> silent, writes peaks; above -> warns
o = run('context-guard', base, {'CONTEXT_LIMIT': '99999999'})
check('guard silent below limit', o is None)
peaks = json.load(open(os.path.join(cfg, '.context-peaks.json')))
check('guard wrote peaks with route=direct', peaks[sid]['route'] == 'direct' and peaks[sid]['peak'] == 300005)
o = run('context-guard', base, {'CONTEXT_LIMIT': '1000'})
check('guard warns above limit (en)', o and 'SESSION CONTEXT' in o['hookSpecificOutput']['additionalContext'])
o = run('context-guard', base, {'CONTEXT_LIMIT': '1000', 'CONTEXT_LANG': 'pt'})
check('guard warns above limit (pt)', o and 'CONTEXTO DA SESSAO' in o['hookSpecificOutput']['additionalContext'])
o = run('context-guard', base, {'CONTEXT_LIMIT': '1000', 'ANTHROPIC_BASE_URL': 'http://127.0.0.1:8790'})
peaks = json.load(open(os.path.join(cfg, '.context-peaks.json')))
check('guard tags route=proxy from ANTHROPIC_BASE_URL', peaks[sid]['route'] == 'proxy')

# batch-eviction: blocks once, then silent
o = run('batch-eviction', base, {'EVICTION_LIMIT': '1000'})
check('eviction blocks with handoff path', o and o['decision'] == 'block' and 'handoff-abcdef12.md' in o['reason'])
o2 = run('batch-eviction', base, {'EVICTION_LIMIT': '1000'})
check('eviction fires once per session', o2 is None)
o3 = run('batch-eviction', {**base, 'stop_hook_active': True, 'session_id': 'x' * 16}, {'EVICTION_LIMIT': '1000'})
check('eviction ignores stop_hook_active', o3 is None)
o4 = run('batch-eviction', {**base, 'session_id': 'y' * 16}, {'EVICTION_LIMIT': '1000', 'CONTEXT_LANG': 'pt'})
check('eviction pt', o4 and 'handoff' in o4['reason'] and 'Contexto' in o4['reason'])

# handoff-load: canary only, then handoff + gen 2, then CANARY=0, then stale handoff
o = run('handoff-load', {'source': 'startup', 'cwd': os.path.join(tmp, 'proj')})
check('handoff-load canary gen1 default name', o and '**ctx · t<N>' in o['hookSpecificOutput']['additionalContext'] and 'gen 2' not in o['hookSpecificOutput']['additionalContext'])
open(os.path.join(proj, 'handoff-abcdef12.md'), 'w', encoding='utf-8').write('# Handoff\n- done: X\n')
o = run('handoff-load', {'source': 'clear', 'cwd': os.path.join(tmp, 'proj')}, {'CANARY_NAME': 'Eduardo', 'CONTEXT_LANG': 'pt'})
t = o['hookSpecificOutput']['additionalContext']
check('handoff-load injects handoff + gen 2 + name (pt)', 'HANDOFF DA SESSAO ANTERIOR' in t and '- done: X' in t and '(gen 2)' in t and '**Eduardo · t<N>' in t)
o = run('handoff-load', {'source': 'resume', 'cwd': os.path.join(tmp, 'proj')})
check('handoff-load silent on resume', o is None)
o = run('handoff-load', {'source': 'startup', 'cwd': os.path.join(tmp, 'proj')}, {'CANARY': '0', 'HANDOFF_HOURS': '0.0000001'})
check('handoff-load silent: canary off + handoff too old', o is None)

# read-recovery
f = os.path.join(tmp, 'file.txt'); open(f, 'w').write('\n'.join(str(i) for i in range(100)) + '\n')
o = run('read-recovery', {'tool_name': 'Read', 'tool_input': {'file_path': f, 'limit': 10}})
check('read-recovery reports remaining lines', o and 'lines 1-10 of 100' in o['hookSpecificOutput']['additionalContext'] and 'offset=11' in o['hookSpecificOutput']['additionalContext'])
o = run('read-recovery', {'tool_name': 'Read', 'tool_input': {'file_path': f, 'limit': 10, 'offset': 95}})
check('read-recovery silent when file exhausted', o is None)
o = run('read-recovery', {'tool_name': 'Read', 'tool_input': {'file_path': f + '.missing', 'limit': 10}})
check('read-recovery silent on missing file', o is None)
o = run('read-recovery', {'tool_name': 'Bash', 'tool_input': {}})
check('read-recovery ignores other tools', o is None)

# install.py against a temp settings.json with a foreign hook
settings = {'env': {'X': '1'}, 'hooks': {'Stop': [{'hooks': [{'type': 'command', 'command': 'node other.js'}]}]}}
json.dump(settings, open(os.path.join(cfg, 'settings.json'), 'w'))
e = {**os.environ, 'CLAUDE_CONFIG_DIR': cfg}
r = subprocess.run([sys.executable, f'{REPO}/hooks/install.py', '--dry-run'], capture_output=True, text=True, env=e, encoding='utf-8')
d = json.loads(r.stdout)
check('install dry-run: 4 events, foreign Stop hook kept, ours added', set(d['hooks']) == {'UserPromptSubmit', 'Stop', 'SessionStart', 'PostToolUse'} and len(d['hooks']['Stop']) == 2 and d['hooks']['PostToolUse'][0]['matcher'] == 'Read' and d['env'] == {'X': '1'})
check('install dry-run wrote nothing', json.load(open(os.path.join(cfg, 'settings.json'))) == settings)
r = subprocess.run([sys.executable, f'{REPO}/hooks/install.py'], capture_output=True, text=True, env=e, encoding='utf-8')
d = json.load(open(os.path.join(cfg, 'settings.json')))
check('install writes + backup', 'installed' in r.stdout and os.path.exists(os.path.join(cfg, 'settings.json.bak')) and len(d['hooks']['Stop']) == 2)
r = subprocess.run([sys.executable, f'{REPO}/hooks/install.py'], capture_output=True, text=True, env=e, encoding='utf-8')
d = json.load(open(os.path.join(cfg, 'settings.json')))
check('install is idempotent', len(d['hooks']['Stop']) == 2 and len(d['hooks']['SessionStart']) == 1)
r = subprocess.run([sys.executable, f'{REPO}/hooks/install.py', '--uninstall'], capture_output=True, text=True, env=e, encoding='utf-8')
d = json.load(open(os.path.join(cfg, 'settings.json')))
check('uninstall leaves only the foreign hook', d['hooks'] == {'Stop': [{'hooks': [{'type': 'command', 'command': 'node other.js'}]}]})
r = subprocess.run([sys.executable, f'{REPO}/hooks/install.py', '--only', 'read-recovery', '--project', os.path.join(tmp, 'proj')], capture_output=True, text=True, env=e, encoding='utf-8')
d = json.load(open(os.path.join(proj, 'settings.json')))
check('install --only --project', list(d['hooks']) == ['PostToolUse'])

# ab-route.py reads the peaks file
r = subprocess.run([sys.executable, f'{REPO}/tools/ab-route.py', '--since', '2000-01-01'], capture_output=True, text=True, env=e, encoding='utf-8')
check('ab-route runs on peaks file', r.returncode == 0 and 'proxy' in r.stdout)

shutil.rmtree(tmp, ignore_errors=True)
print('\nfails:', fails)
sys.exit(1 if fails else 0)
