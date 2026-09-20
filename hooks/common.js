// Shared helpers for the hooks: read stdin JSON, measure the current context
// from the transcript tail, read/write the per-session peaks file.
'use strict';
const fs = require('fs');
const path = require('path');
const os = require('os');

const claudeDir = process.env.CLAUDE_CONFIG_DIR || path.join(os.homedir(), '.claude');
const peaksPath = path.join(claudeDir, '.context-peaks.json');

// Context of the last real API call = input + cache_creation + cache_read: that
// is what the next call re-sends. Reads the tail of the transcript; some
// assistant lines carry a zeroed usage (synthetic), so keep walking back until
// a real call shows up. The tail grows if needed.
// Right after /compact the tail ends with a compact_boundary line and no call
// yet: the old usage would be the pre-compaction size, and postTokens is only
// the summary (measured 2-12x below the first real call), so report unknown.
// A "compact_boundary" quoted inside a tool_result comes escaped
// (\"compact_boundary\") and does not match.
function currentContext(transcriptPath) {
  const st = fs.statSync(transcriptPath);
  for (const len of [262144, 4194304].map(n => Math.min(n, st.size))) {
    const fd = fs.openSync(transcriptPath, 'r');
    const buf = Buffer.alloc(len);
    fs.readSync(fd, buf, 0, len, st.size - len);
    fs.closeSync(fd);
    const lines = buf.toString('utf8').split('\n');
    for (let i = lines.length - 1; i >= 0; i--) {
      if (lines[i].indexOf('"compact_boundary"') !== -1) return 0;
      if (lines[i].indexOf('"usage"') === -1) continue;
      let e;
      try { e = JSON.parse(lines[i]); } catch (_) { continue; }
      const u = e && e.message && e.message.usage;
      if (!u) continue;
      const ctx = (u.input_tokens || 0) + (u.cache_creation_input_tokens || 0) + (u.cache_read_input_tokens || 0);
      if (ctx > 0) return ctx;
    }
    if (len === st.size) break;
  }
  return 0;
}

// {} when the file is missing or empty; null when it exists but cannot be read
// or does not parse (another session mid-write, another process holding it
// open): callers must not write over it.
function readPeaks() {
  let raw;
  try { raw = fs.readFileSync(peaksPath, 'utf8'); } catch (e) { return e.code === 'ENOENT' ? {} : null; }
  if (!raw.trim()) return {};
  try { return JSON.parse(raw); } catch (_) { return null; }
}

// Write to a temp file and rename it into place: sessions run in parallel and
// a reader must never see a half-written file.
function writePeaks(peaks) {
  const tmp = peaksPath + '.' + process.pid + '.tmp';
  fs.writeFileSync(tmp, JSON.stringify(peaks, null, 1));
  try { fs.renameSync(tmp, peaksPath); } catch (e) { fs.unlinkSync(tmp); throw e; }
}

function sessionId(data) {
  return data.session_id || path.basename(data.transcript_path, '.jsonl');
}

function k(n) { return Math.round(n / 1000) + 'k'; }

// A hook that dies with a stack trace (exit 1) is shown to the user on every
// prompt; one line on stderr and exit 0 keeps the failure visible in --debug
// without shouting or blocking.
function readStdin(cb) {
  let raw = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', c => { raw += c; });
  process.stdin.on('end', () => {
    let data;
    try { data = JSON.parse(raw); } catch (_) { return; }
    try { cb(data); } catch (e) {
      process.stderr.write(path.basename(process.argv[1]) + ': ' + String(e.message || e).replace(/\s+/g, ' ') + '\n');
    }
  });
}

module.exports = { claudeDir, peaksPath, currentContext, readPeaks, writePeaks, sessionId, k, readStdin };
