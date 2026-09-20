#!/usr/bin/env node
// context-guard — UserPromptSubmit hook, per session.
//
// Reads the context size of this session's last API call (input +
// cache_creation + cache_read = what the next turn re-sends) and, above the
// limit, warns the model on EVERY turn. Records the per-session peak in
// ~/.claude/.context-peaks.json.
//
// Why: measured on 655 sessions (2026-09-13), 65% of all cache reads came from
// calls with context >= 320k. A global-counter guard fired 85 times in 3
// months and never described the actual session. Ref.: TokenPilot
// (arXiv 2606.17016), eq. 2.
//
// Limit: CONTEXT_LIMIT (default 200000 tokens). Language: CONTEXT_LANG=pt.
'use strict';
const fs = require('fs');
const S = require('./lang');
const { currentContext, readPeaks, writePeaks, sessionId, k, readStdin, lockPeaks } = require('./common');

const LIMIT = parseInt(process.env.CONTEXT_LIMIT, 10) || 200000;

readStdin(data => {
  if (!data.transcript_path || !fs.existsSync(data.transcript_path)) return;
  const ctx = currentContext(data.transcript_path);
  if (!ctx) return;

  // The lock serialises read -> write across sessions; without it the warning still goes out.
  let unlock = null;
  try { unlock = lockPeaks(); } catch (e) {
    process.stderr.write('context-guard.js: ' + String(e.message || e).replace(/\s+/g, ' ') + '\n');
  }
  // null = the file exists but could not be read or parsed (another session mid-write): warn, do not write.
  const peaks = unlock ? readPeaks() : null;
  const sid = sessionId(data);
  const p = (peaks && peaks[sid]) || { peak: 0, turns_above: 0, project: data.cwd || '' };
  p.peak = Math.max(p.peak, ctx);
  p.last = new Date().toISOString();
  p.transcript = data.transcript_path;   // handoff-load.js names it to the next session
  // Route tag for A/B of launch paths (tools/ab-route.py): a session launched
  // through a local proxy inherits ANTHROPIC_BASE_URL on loopback.
  p.route = /127\.0\.0\.1|localhost/.test(process.env.ANTHROPIC_BASE_URL || '') ? 'proxy' : 'direct';
  if (ctx >= LIMIT) p.turns_above += 1;
  if (peaks) {
    peaks[sid] = p;
    // Bookkeeping only: a failed write must not swallow the warning below.
    try { writePeaks(peaks); } catch (e) {
      process.stderr.write('context-guard.js: ' + String(e.message || e).replace(/\s+/g, ' ') + '\n');
    }
  }
  if (unlock) unlock();

  if (ctx < LIMIT) return;
  process.stdout.write(JSON.stringify({
    hookSpecificOutput: {
      hookEventName: 'UserPromptSubmit',
      additionalContext: S.guard(k(ctx), k(LIMIT), k(p.peak), p.turns_above)
    }
  }));
});
