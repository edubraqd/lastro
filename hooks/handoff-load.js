#!/usr/bin/env node
// handoff-load — SessionStart hook. Pair of batch-eviction.js.
//
// After /clear (or a new session in the same project) injects the newest
// <project root>/.claude/handoff-*.md that can be loaded: younger than HANDOFF_HOURS
// (default 72), written by a session that ran on this machine, not loaded yet.
// Files are walked newest to oldest: one that is foreign or already consumed
// does not block an older own one; one that is too old ends the walk. The load
// is marked in the peaks file BEFORE the text is injected, so a handoff is never
// delivered twice, and the canary never depends on that mark being written.
// Only for source "clear" and "startup"; resume/compact already carry history
// (the installer registers the matcher; the check below is defence in depth).
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
const { readStdin, readPeaks, writePeaks, lockPeaks, projectDir } = require('./common');

// HANDOFF_HOURS=0 turns the handoff off (a harness of `claude -p` runs opts out);
// `parseFloat(x) || 72` used to swallow the 0.
const HOURS = (v => isNaN(v) ? 72 : v)(parseFloat(process.env.HANDOFF_HOURS));
const CANARY = process.env.CANARY !== '0';
const NAME = process.env.CANARY_NAME || 'Lastro';

readStdin(data => {
  if (data.source && data.source !== 'clear' && data.source !== 'startup') return;
  const parts = [];
  let gen = 1;
  const sid = data.session_id || '';

  const dir = path.join(projectDir(data), '.claude');   // the root, not the cd target
  // The path this session itself would write: the canary's TRIP names it.
  const own = sid ? path.join(dir, 'handoff-' + sid.slice(0, 8) + '.md') : null;
  const msg = e => String(e.message || e).replace(/\s+/g, ' ');
  try {
    if (HOURS <= 0) {
      process.stderr.write('handoff-load: handoff off (HANDOFF_HOURS=0)\n');
    } else if (fs.existsSync(dir)) {
      const cands = fs.readdirSync(dir)
        .filter(n => /^handoff-[0-9a-f]{8}\.md$/.test(n))
        .map(n => ({ n, p: path.join(dir, n), t: fs.statSync(path.join(dir, n)).mtimeMs }))
        .sort((a, b) => b.t - a.t);
      if (cands.length) {
        // Provenance: the file name carries 8 hex of a session id, and context-guard
        // writes every session that ran here into the peaks file. A handoff-*.md
        // that arrived by git clone or copy has mtime = now and would pass on age
        // alone; it is data from outside, not this machine's memory, and it does
        // not shadow an older own file. Each handoff is loaded once (a rewrite of
        // the same file, newer than the load, counts as new): two sessions opened
        // in the same project must not both resume it, but the one already
        // consumed does not hide an older one still waiting.
        // One session at a time between reading the marks and writing its own:
        // parallel starts otherwise all read "not loaded" (measured 2-6 of 28).
        let unlock = null;
        try { unlock = lockPeaks(); } catch (e) {
          process.stderr.write('handoff-load: skipping ' + cands[0].n + ': ' + msg(e) + '\n');
          parts.push(S.handoffSkipped(cands[0].n, 'could not record the load: ' + msg(e)));
        }
        const peaks = unlock ? readPeaks() : null;
        let skipped = null;   // {n, why}: the newest file refused for a reason the model should know
        if (unlock) try { for (const h of cands) {
          // exFAT reports an mtime up to 2 s ahead of the clock: never a negative age
          const age = Math.max(0, Date.now() - h.t) / 3600000;
          const owner = Object.keys(peaks || {}).find(s => s.startsWith(h.n.slice(8, 16)));
          const rec = owner && peaks[owner];
          // mtime against mtime, not against a clock: a load inside that 2 s skew
          // would not count. handoff_loaded_at stays for humans and as the fallback
          // for peaks written before the mtime mark existed.
          const loaded = rec && (rec.handoff_loaded_mtime != null
            ? rec.handoff_loaded_mtime >= h.t
            : rec.handoff_loaded_at && Date.parse(rec.handoff_loaded_at) >= h.t);
          if (age > HOURS) {
            process.stderr.write('handoff-load: skipping ' + h.n + ': ' + age.toFixed(1) + ' h old (HANDOFF_HOURS=' + HOURS + ')\n');
            break;   // sorted: the rest are older still
          } else if (!peaks) {
            process.stderr.write('handoff-load: skipping ' + h.n + ': peaks file unreadable, cannot check where it came from\n');
            if (!skipped) skipped = { n: h.n, why: 'peaks file unreadable' };
            break;
          } else if (!owner) {
            process.stderr.write('handoff-load: skipping ' + h.n + ': no session with that id ran on this machine\n');
            continue;
          } else if (loaded) {
            process.stderr.write('handoff-load: skipping ' + h.n + ': already loaded by session ' + rec.handoff_loaded_by + '\n');
            if (!skipped) skipped = { n: h.n, why: 'already loaded by session ' + rec.handoff_loaded_by };
            continue;
          }
          const raw = fs.readFileSync(h.p, 'utf8');
          // The wrapper tag is ours: a body that quotes it must not close it.
          const text = raw.slice(0, 12000).replace(/<(\/?)handoff\b/gi, '&lt;$1handoff');
          const tr = rec.transcript && fs.existsSync(rec.transcript) ? rec.transcript : null;
          rec.handoff_loaded_at = new Date().toISOString();
          rec.handoff_loaded_mtime = h.t;
          rec.handoff_loaded_by = sid;
          // Mark BEFORE injecting: if the mark cannot be written the handoff is
          // skipped (never loaded twice), the peaks file is untouched and the next
          // /clear retries. The canary below never depends on this.
          try { writePeaks(peaks); } catch (e) {
            process.stderr.write('handoff-load: skipping ' + h.n + ': could not record the load (' + msg(e) + ')\n');
            if (!skipped) skipped = { n: h.n, why: 'could not record the load: ' + msg(e) };
            break;
          }
          // The cut note sits outside the wrapper, with the absolute path: it is
          // the hook's line, not the previous session's notes.
          parts.push(S.handoff(h.n, age.toFixed(1), tr) + '\n<handoff file="' + h.n + '">\n' + text + '\n</handoff>' +
            (raw.length > 12000 ? '\n' + S.cut(12000, h.p) : ''));
          gen = 2;
          skipped = null;
          break;
        } } finally { unlock(); }
        if (skipped) parts.push(S.handoffSkipped(skipped.n, skipped.why));
      }
    }
  } catch (e) {
    // A failed stat/read (candidate deleted between readdir and stat, etc.)
    // must not cost the canary.
    process.stderr.write('handoff-load: skipping handoff: ' + msg(e) + '\n');
  }
  // HANDOFF_HOURS=0: nothing would load a handoff, so the TRIP does not ask for one.
  if (CANARY) parts.push(S.canary(NAME, gen, HOURS > 0 ? own : false));
  if (!parts.length) return;
  process.stdout.write(JSON.stringify({
    hookSpecificOutput: {
      hookEventName: 'SessionStart',
      additionalContext: parts.join('\n\n')
    }
  }));
});
