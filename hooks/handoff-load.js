#!/usr/bin/env node
// handoff-load — SessionStart hook. Pair of batch-eviction.js.
//
// After /clear (or a new session in the same project) injects the most recent
// <cwd>/.claude/handoff-*.md if it is younger than HANDOFF_HOURS (default 12).
// Only for source "clear" and "startup"; resume/compact already carry history.
//
// Also installs the context canary (after JuliusBrussee/skills, context-canary):
// a fixed line at the top of every reply whose only job is to disappear when
// the old instruction falls out of context. context-guard.js measures tokens;
// the canary measures adherence — different failures. Disable: CANARY=0.
// Name shown in the line: CANARY_NAME (default "Lastro"). Language: CONTEXT_LANG=pt.
'use strict';
const fs = require('fs');
const path = require('path');
const S = require('./lang');
const { readStdin } = require('./common');

const HOURS = parseFloat(process.env.HANDOFF_HOURS) || 12;
const CANARY = process.env.CANARY !== '0';
const NAME = process.env.CANARY_NAME || 'Lastro';

readStdin(data => {
  if (data.source && data.source !== 'clear' && data.source !== 'startup') return;
  const parts = [];
  let gen = 1;

  const dir = path.join(data.cwd || process.cwd(), '.claude');
  if (fs.existsSync(dir)) {
    const cands = fs.readdirSync(dir)
      .filter(n => /^handoff-[0-9a-f]{8}\.md$/.test(n))
      .map(n => ({ n, p: path.join(dir, n), t: fs.statSync(path.join(dir, n)).mtimeMs }))
      .sort((a, b) => b.t - a.t);
    if (cands.length) {
      const h = cands[0];
      const age = (Date.now() - h.t) / 3600000;
      if (age <= HOURS) {
        const text = fs.readFileSync(h.p, 'utf8').slice(0, 12000);
        parts.push(S.handoff(h.n, age.toFixed(1)) + '\n\n' + text);
        gen = 2;
      }
    }
  }
  if (CANARY) parts.push(S.canary(NAME, gen));
  if (!parts.length) return;
  process.stdout.write(JSON.stringify({
    hookSpecificOutput: {
      hookEventName: 'SessionStart',
      additionalContext: parts.join('\n\n')
    }
  }));
});
