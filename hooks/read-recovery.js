#!/usr/bin/env node
// read-recovery — PostToolUse hook for Read.
//
// When a Read carries a `limit` (yours, or injected by a PreToolUse hook that
// bounds tool input), the result ends dry: nothing says the file continues.
// This hook counts the file's lines and, if some are left, tells the model the
// offset to continue from. It is TokenPilot's "recovery tool" (arXiv
// 2606.17016, §3.2): cutting without a way back lowers accuracy and makes the
// agent repeat calls. Language: CONTEXT_LANG=pt.
'use strict';
const fs = require('fs');
const S = require('./lang');
const { readStdin } = require('./common');

readStdin(data => {
  if (data.tool_name !== 'Read') return;
  const inp = data.tool_input || {};
  if (!inp.file_path || !inp.limit || inp.pages) return;
  // Read answers image/pdf/notebook Reads without lines; an injected limit reaches those too.
  const r = data.tool_response;
  if (r && typeof r === 'object' && r.type && r.type !== 'text') return;
  let st;
  try { st = fs.statSync(inp.file_path); } catch (_) { return; }
  if (!st.isFile() || st.size > 50 * 1024 * 1024) return;
  const buf = fs.readFileSync(inp.file_path);
  let total = 0;
  for (let i = 0; i < buf.length; i++) if (buf[i] === 10) total++;
  if (buf.length && buf[buf.length - 1] !== 10) total++;
  const start = inp.offset || 1;
  const end = start + inp.limit - 1;
  if (end >= total) return;
  process.stdout.write(JSON.stringify({
    hookSpecificOutput: {
      hookEventName: 'PostToolUse',
      additionalContext: S.readCut(start, end, total, end + 1)
    }
  }));
});
