#!/usr/bin/env node
// mission-arm — UserPromptExpansion hook, matcher missao.
//
// /missao <text> arms a mission (zelador/missao.py) that keeps going across clear_session("self").
// Without this hook the text reaches the mission file through the model: the command tells it to
// Write the text and hand it to `missao.py armar`, and a summary or a correction there is a wrong
// mission in every later generation. Here the text is taken as the user typed it and given to
// that same script, before the model reads the command.
//
// Measured 09/11 on CLI 2.1.317, headless, prompt by argv and by stream-json: a typed /command
// fires UserPromptSubmit (prompt as typed) and then UserPromptExpansion, which carries
// command_name and command_args (newlines and accents kept); the additionalContext of both is
// attached after the expanded command.
//
// Only in a desktop session (CLAUDE_CODE_HOST_SESSION_ID) and only with text: a bare /missao
// arms nothing. Arming again replaces the mission, as the command always did.
// Any failure (no python, the script refused) leaves no output: the command, which arms by
// itself when this hook's line is absent, still does it the old way.
'use strict';
const path = require('path');
const { spawnSync } = require('child_process');
const S = require('./lang');
const { readStdin, projectDir, mission } = require('./common');

readStdin(data => {
  if (data.command_name !== 'missao') return;
  const text = String(data.command_args || '');
  if (!text.trim()) return;
  if (!/^local_[\w-]+$/.test(process.env.CLAUDE_CODE_HOST_SESSION_ID || '')) return;

  // The scheme of the mission file lives in missao.py: the text goes in by stdin, untouched by a shell.
  const script = path.join(__dirname, '..', 'zelador', 'missao.py');
  let r;
  for (const py of ['python', 'python3']) {
    r = spawnSync(py, [script, 'armar'], { input: text, cwd: projectDir(data), timeout: 4000, windowsHide: true,
      env: Object.assign({}, process.env, { PYTHONIOENCODING: 'utf-8' }) });
    if (!(r.error && r.error.code === 'ENOENT')) break;
  }
  if (r.error || r.status !== 0) {
    throw new Error('missao.py armar: ' + (r.error ? r.error.message : String(r.stderr).trim().split('\n').pop()));
  }
  const z = mission();
  if (!z) return;
  process.stdout.write(JSON.stringify({
    hookSpecificOutput: { hookEventName: 'UserPromptExpansion', additionalContext: S.missionArmed(z.file, z.watched) }
  }));
});
