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
function currentContext(transcriptPath) {
  const st = fs.statSync(transcriptPath);
  for (const len of [262144, 4194304].map(n => Math.min(n, st.size))) {
    const fd = fs.openSync(transcriptPath, 'r');
    const buf = Buffer.alloc(len);
    fs.readSync(fd, buf, 0, len, st.size - len);
    fs.closeSync(fd);
    const lines = buf.toString('utf8').split('\n');
    for (let i = lines.length - 1; i >= 0; i--) {
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

function readPeaks() {
  try { return JSON.parse(fs.readFileSync(peaksPath, 'utf8')); } catch (_) { return {}; }
}

function writePeaks(peaks) {
  fs.writeFileSync(peaksPath, JSON.stringify(peaks, null, 1));
}

function sessionId(data) {
  return data.session_id || path.basename(data.transcript_path, '.jsonl');
}

function k(n) { return Math.round(n / 1000) + 'k'; }

function readStdin(cb) {
  let raw = '';
  process.stdin.on('data', c => { raw += c; });
  process.stdin.on('end', () => {
    let data;
    try { data = JSON.parse(raw); } catch (_) { return; }
    cb(data);
  });
}

module.exports = { claudeDir, peaksPath, currentContext, readPeaks, writePeaks, sessionId, k, readStdin };
