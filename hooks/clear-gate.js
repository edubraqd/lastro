#!/usr/bin/env node
// clear-gate — PreToolUse hook, matcher mcp__ccd_session_mgmt__clear_session.
//
// The desktop app's clear_session("self") stops the CLI when the turn ends, and nothing comes
// back up without a message (measured 08/11). A mission the user armed in a session
// (zelador/missao.py) keeps going across that clear: this gate files a request, the keeper's
// watcher (zelador/vigia.py) waits for this CLI to exit, and the keeper session sends "segue".
//
// It decides only for session_id "self" in a desktop session with an armed mission. Anything
// else leaves no decision: the normal permission flow stays as it was. With a mission:
//   no watcher alive                 deny  (nobody would send "segue")
//   no handoff by this generation    deny  (the next one would start blind)
//   the mission's clear limit hit    deny  (a loop that clears without progress stops here)
//   context below the minimum        deny  (a clear is for a full context)
//   otherwise                        file the request, count the clear, allow
// A second call by the same generation rewrites its request and counts nothing.
// Any failure (state unreadable, request not written) leaves no decision.
'use strict';
const fs = require('fs');
const path = require('path');
const S = require('./lang');
const { readStdin, readPeaks, projectDir, sessionId, currentContext, mission, readJson, zDir, k } = require('./common');

function decide(decision, reason) {
  process.stdout.write(JSON.stringify({
    hookSpecificOutput: { hookEventName: 'PreToolUse', permissionDecision: decision, permissionDecisionReason: reason }
  }));
}

function writeJson(file, obj) {
  const tmp = file + '.' + process.pid + '.tmp';
  fs.writeFileSync(tmp, JSON.stringify(obj, null, 1));
  try { fs.renameSync(tmp, file); } catch (e) { fs.unlinkSync(tmp); throw e; }
}

readStdin(data => {
  if (!/clear_session$/.test(data.tool_name || '') || !data.tool_input || data.tool_input.session_id !== 'self') return;
  const z = mission();
  if (!z) return;
  if (!z.watched) return decide('deny', S.gateNoKeeper());

  const sid = sessionId(data);
  const file = path.join(projectDir(data), '.claude', 'handoff-' + sid.slice(0, 8) + '.md');
  // This generation's birth: the start record (handoff-load), else the transcript's own.
  const peaks = readPeaks();
  let born = Date.parse((peaks && peaks[sid] && peaks[sid].started) || '');
  if (isNaN(born)) try { born = fs.statSync(data.transcript_path).birthtimeMs; } catch (_) { born = 0; }
  let written = 0;
  try { written = fs.statSync(file).mtimeMs; } catch (_) { /* none */ }
  // exFAT stamps an mtime up to 2 s off the clock
  if (!written || written < born - 2000) return decide('deny', S.gateNoHandoff(file));

  const dir = path.join(zDir, 'pedidos');
  const reqPath = path.join(dir, z.host + '.json');
  const old = readJson(reqPath);
  const again = !!old && old.sid === sid;
  const n = z.m.ciclos || 0;
  const max = z.m.max_ciclos || 10;
  if (!again && n >= max) return decide('deny', S.gateCap(max));
  const min = z.m.min_ctx == null ? 150000 : z.m.min_ctx;
  let ctx = 0;
  try { ctx = currentContext(data.transcript_path); } catch (_) { /* unknown: not held against it */ }
  if (ctx && ctx < min) return decide('deny', S.gateSmall(k(ctx), k(min)));

  // The process the watcher waits on. Without it there is no request to file: normal flow.
  const pid = parseInt(process.env.CLAUDE_PID, 10);
  if (!(pid > 0)) return;
  const ciclo = again ? old.ciclo : n + 1;
  fs.mkdirSync(dir, { recursive: true });
  writeJson(reqPath, { host: z.host, pid, sid, transcript: data.transcript_path || null, handoff: file,
    hora: new Date().toISOString(), ciclo });
  if (!again) {
    z.m.ciclos = ciclo;
    z.m.ultimo_clear = new Date().toISOString();
    writeJson(z.file, z.m);
  }
  decide('allow', S.gateOk(ciclo));
});
