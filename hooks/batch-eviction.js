#!/usr/bin/env node
// batch-eviction — Stop hook. Batch eviction with a summary (TokenPilot §3.3;
// "Less Context, Better Agents" C4: prune + short summary of what was done).
//
// When a turn ends with the context above the limit, ONCE per session, it
// holds the Stop and makes the model write a handoff to
// <project root>/.claude/handoff-<session>.md (CLAUDE_PROJECT_DIR) and tell the
// user to run /clear. HANDOFF_HOURS=0 turns it off, as in handoff-load.js.
// handoff-load.js (SessionStart) re-injects that file after /clear.
// Per-session record in ~/.claude/.context-peaks.json.
//
// Limit: EVICTION_LIMIT (default 150000 tokens). Language: CONTEXT_LANG=pt.
'use strict';
const fs = require('fs');
const path = require('path');
const S = require('./lang');
const { currentContext, readPeaks, writePeaks, sessionId, k, readStdin, lockPeaks, projectDir } = require('./common');

const LIMIT = parseInt(process.env.EVICTION_LIMIT, 10) || 150000;
// Same reading as handoff-load.js: 0 = handoff off (nothing would load it).
const HOURS = (v => isNaN(v) ? 72 : v)(parseFloat(process.env.HANDOFF_HOURS));

readStdin(data => {
  if (HOURS <= 0 || data.stop_hook_active) return;
  if (!data.transcript_path || !fs.existsSync(data.transcript_path)) return;
  const ctx = currentContext(data.transcript_path);
  if (ctx < LIMIT) return;

  const sid = sessionId(data);
  // null = the file exists but did not parse (another session mid-write): without it
  // there is no way to tell whether this session already got its handoff; next turn.
  let unlock;
  try { unlock = lockPeaks(); } catch (e) {
    process.stderr.write('batch-eviction.js: ' + String(e.message || e).replace(/\s+/g, ' ') + '\n');
    return;   // next turn retries
  }
  let file;
  try {
    const peaks = readPeaks();
    if (!peaks) return;
    const p = peaks[sid] || { peak: 0, turns_above: 0, project: data.cwd || '' };
    if (p.handoff) return;

    // Under the project root, not the folder the session has cd-ed into.
    file = path.join(projectDir(data), '.claude', 'handoff-' + sid.slice(0, 8) + '.md');
    p.handoff = file;
    p.handoff_at = new Date().toISOString();
    p.transcript = data.transcript_path;   // handoff-load.js names it to the next session
    peaks[sid] = p;
    writePeaks(peaks);
  } finally { unlock(); }

  process.stdout.write(JSON.stringify({
    decision: 'block',
    reason: S.evict(k(ctx), file)
  }));
});
