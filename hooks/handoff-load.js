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
// Sibling sessions in one project: only a handoff of this session's own lineage loads
// (common.js lineage(): the desktop session, or the CLI process of a terminal /clear). A new
// session takes none from a sibling, except from a terminal session that has exited. A
// session that does not know its own lineage (an older CLI) keeps the walk above.
// The start puts the session on record in the peaks file (F4, 08/11): the guard does so only
// from the second prompt on, and a generation that worked one long turn had its handoff
// refused as "no session with that id ran on this machine".
// Desktop generations (lineage host:) run in series, one CLI per app session at a time, so
// "once" gives way there: when the generation that took the newest handoff of the lineage
// left none of its own, that handoff loads again, naming that generation's transcript (F3);
// a previous generation that ended without a handoff (a /clear, or a CLI that exited on its
// own) is named with its transcript (F5). A terminal keeps the one-time load: its lineage is
// a pid the OS reuses, and two new terminal sessions may both inherit one that exited.
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
const { readStdin, readPeaks, writePeaks, lockPeaks, projectDir, lineage, alive, mission } = require('./common');

// HANDOFF_HOURS=0 turns the handoff off (a harness of `claude -p` runs opts out);
// `parseFloat(x) || 72` used to swallow the 0.
const HOURS = (v => isNaN(v) ? 72 : v)(parseFloat(process.env.HANDOFF_HOURS));
const CANARY = process.env.CANARY !== '0';
const NAME = process.env.CANARY_NAME || 'Lastro';

// '' when a session of lineage `mine` may load a handoff whose owner record is rec; else why not.
function foreign(rec, mine, source) {
  if (!rec.lineage) return 'its session recorded no lineage (it ran before the lineage check)';
  if (rec.lineage === mine) return '';
  // a terminal session that has exited is no sibling any more: a new session may resume its work
  if (source !== 'clear' && mine.startsWith('pid:') && rec.lineage.startsWith('pid:') &&
      !alive(parseInt(rec.lineage.slice(4), 10))) return '';
  return 'it belongs to another session (' + rec.lineage + ')';
}

// The session of lineage `mine` that ran last before `sid`, if inside the handoff window.
// Generations of one desktop session never overlap: any of their stamps orders them.
function previous(peaks, mine, sid) {
  let prev = null;
  for (const s of Object.keys(peaks)) {
    const r = peaks[s];
    if (s === sid || !r || r.lineage !== mine) continue;
    const at = [r.started, r.last].filter(Boolean).sort().pop() || '';
    if (!prev || at > prev.at) prev = { sid: s, rec: r, at };
  }
  return prev && Date.now() - Date.parse(prev.at) <= HOURS * 3600000 ? prev : null;
}

// A transcript worth naming: recorded and still on disk.
function transcriptOf(rec) {
  return rec && rec.transcript && fs.existsSync(rec.transcript) ? rec.transcript : null;
}

readStdin(data => {
  if (data.source && data.source !== 'clear' && data.source !== 'startup') return;
  const parts = [];
  let gen = 1;
  const sid = data.session_id || '';
  const mine = lineage();
  const serial = mine.startsWith('host:');   // desktop: generations in series

  const dir = path.join(projectDir(data), '.claude');   // the root, not the cd target
  // The path this session itself would write: the canary's TRIP names it.
  const own = sid ? path.join(dir, 'handoff-' + sid.slice(0, 8) + '.md') : null;
  const msg = e => String(e.message || e).replace(/\s+/g, ' ');
  try {
    if (HOURS <= 0) {
      process.stderr.write('handoff-load: handoff off (HANDOFF_HOURS=0)\n');
    } else {
      const cands = (fs.existsSync(dir) ? fs.readdirSync(dir) : [])
        .filter(n => /^handoff-[0-9a-f]{8}\.md$/.test(n))
        .map(n => ({ n, p: path.join(dir, n), t: fs.statSync(path.join(dir, n)).mtimeMs }))
        .sort((a, b) => b.t - a.t);
      // Provenance: the file name carries 8 hex of a session id, and the start (or
      // context-guard) writes every session that ran here into the peaks file. A handoff-*.md
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
        if (cands.length) {
          process.stderr.write('handoff-load: skipping ' + cands[0].n + ': could not record the load (' + msg(e) + ')\n');
          parts.push(S.handoffSkipped(cands[0].n, 'could not record the load: ' + msg(e)));
        } else process.stderr.write('handoff-load: could not record the session (' + msg(e) + ')\n');
      }
      if (unlock) try {
        const peaks = readPeaks();
        if (peaks && sid) {
          const p = peaks[sid] || { peak: 0, turns_above: 0, project: data.cwd || '' };
          p.started = p.started || new Date().toISOString();
          if (data.transcript_path) p.transcript = data.transcript_path;
          p.lineage = mine || p.lineage;
          peaks[sid] = p;
        }
        const refused = [];   // {n, why, own}: files not loaded; the note prefers the own lineage's
        let again = null;     // the generation that loaded it before, when a handoff loads again
        let wrote = false, failed = false;
        for (const h of cands) {
          // exFAT reports an mtime up to 2 s ahead of the clock: never a negative age
          const age = Math.max(0, Date.now() - h.t) / 3600000;
          const owner = Object.keys(peaks || {}).find(s => s.startsWith(h.n.slice(8, 16)));
          const rec = owner && peaks[owner];
          let why = '';
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
            refused.push({ n: h.n, why: 'peaks file unreadable' });
            break;
          } else if (!owner) {
            process.stderr.write('handoff-load: skipping ' + h.n + ': no session with that id ran on this machine\n');
            continue;
          } else if (mine && (why = foreign(rec, mine, data.source))) {
            process.stderr.write('handoff-load: skipping ' + h.n + ': ' + why + '\n');
            refused.push({ n: h.n, why });
            continue;
          } else if (loaded && !serial) {
            why = 'already loaded by session ' + rec.handoff_loaded_by;
            process.stderr.write('handoff-load: skipping ' + h.n + ': ' + why + '\n');
            refused.push({ n: h.n, why, own: !!mine && rec.lineage === mine });
            continue;
          }
          again = (loaded && rec.handoff_loaded_by) || null;
          const raw = fs.readFileSync(h.p, 'utf8');
          // The wrapper tag is ours: a body that quotes it must not close it.
          const text = raw.slice(0, 12000).replace(/<(\/?)handoff\b/gi, '&lt;$1handoff');
          const tr = transcriptOf(rec);
          rec.handoff_loaded_at = new Date().toISOString();
          rec.handoff_loaded_mtime = h.t;
          rec.handoff_loaded_by = sid;
          // Mark BEFORE injecting: if the mark cannot be written the handoff is
          // skipped (never loaded twice), the peaks file is untouched and the next
          // /clear retries. The canary below never depends on this.
          try { writePeaks(peaks); wrote = true; } catch (e) {
            failed = true;
            process.stderr.write('handoff-load: skipping ' + h.n + ': could not record the load (' + msg(e) + ')\n');
            refused.push({ n: h.n, why: 'could not record the load: ' + msg(e), own: !!mine });
            break;
          }
          // The cut note sits outside the wrapper, with the absolute path: it is
          // the hook's line, not the previous session's notes.
          parts.push(S.handoff(h.n, age.toFixed(1), tr) +
            (again ? ' ' + S.handoffAgain(again, transcriptOf(peaks[again])) : '') +
            '\n<handoff file="' + h.n + '">\n' + text + '\n</handoff>' +
            (raw.length > 12000 ? '\n' + S.cut(12000, h.p) : ''));
          gen = 2;
          refused.length = 0;
          break;
        }
        // Nothing loaded: the record alone. Never after a failed mark, which the object still carries.
        if (peaks && sid && !wrote && !failed) {
          try { writePeaks(peaks); } catch (e) {
            process.stderr.write('handoff-load: could not record the session (' + msg(e) + ')\n');
          }
        }
        // The generation before this one left no handoff: say so, unless the reload above already does.
        const prev = serial && peaks ? previous(peaks, mine, sid) : null;
        if (prev && prev.sid !== again && !fs.existsSync(path.join(dir, 'handoff-' + prev.sid.slice(0, 8) + '.md'))) {
          parts.push(S.handoffNone(prev.sid, transcriptOf(prev.rec)));
        }
        const note = refused.find(r => r.own) || refused[0];
        if (note) parts.push(S.handoffSkipped(note.n, note.why));
      } finally { unlock(); }
    }
  } catch (e) {
    // A failed stat/read (candidate deleted between readdir and stat, etc.)
    // must not cost the canary.
    process.stderr.write('handoff-load: skipping handoff: ' + msg(e) + '\n');
  }
  // Zelador: every generation of a session with an armed mission starts from the user's own words.
  try {
    const z = HOURS > 0 ? mission() : null;
    if (z) {
      const done = 'python "' + path.join(__dirname, '..', 'zelador', 'missao.py').replace(/\\/g, '/') + '" concluir';
      parts.push(S.missionStart(String(z.m.texto || '').slice(0, 6000).replace(/<(\/?)mission\b/gi, '&lt;$1mission'),
        z.m.ciclos || 0, z.m.max_ciclos || 10, done));
    }
  } catch (e) {
    process.stderr.write('handoff-load: skipping mission: ' + msg(e) + '\n');
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
