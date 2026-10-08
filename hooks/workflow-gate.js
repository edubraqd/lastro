#!/usr/bin/env node
// workflow-gate - PreToolUse hook, matcher Workflow|Agent|Task.
//
// Logs every Workflow and Agent launch to ~/.claude/workflow-gate.csv with
// whether the last human prompt asked for it. With WORKFLOW_GATE=ask, a
// Workflow nobody asked for goes to the user for approval instead of running.
// Agent calls are logged, never gated: one call is one agent, and the Agent
// fan-out (15.9% of spend since 24/08) needs its own baseline first.
//
// Why: measured 2026-10-03 on 216 runs (3,743 agents): 207 of the 211 runs
// launched with ultracode on had no request in the turn, US$ 3,781 of 4,065.
// The size guideline is advice and ultracode overrides it; a hook is the only
// check that runs before the agents spawn. The default mode only logs, so the
// share of unrequested launches is measured before anything is gated.
//
// "Asked" = the last human prompt matches REQUEST, or the CLI attached a
// workflow_keyword_request to it. Same rule as tools/medir_workflows.py.
'use strict';
const fs = require('fs');
const path = require('path');
const S = require('./lang');
const { claudeDir, sessionId, readStdin } = require('./common');

const MODE = (process.env.WORKFLOW_GATE || 'log').toLowerCase();
const LOG = path.join(claudeDir, 'workflow-gate.csv');
const TOOLS = ['Workflow', 'Agent', 'Task'];
const TAIL = 4 * 1024 * 1024;   // the last prompt is near the end; long transcripts reach 50 MB
const SKIP = ['<task-notification>', '<local-command-stdout>', '<local-command-stderr>', '<local-command-caveat>', 'Caveat:'];
const REQUEST = /ultracode|workflow|deep[- ]?research|sub-?agent|\bagentes?\b|\bagents?\b|multi-?agent|orquestr|em paralelo|in parallel|fan-?out|swarm/i;

function textOf(content) {
  if (typeof content === 'string') return content;
  if (!Array.isArray(content)) return '';
  return content.filter(b => b && b.type === 'text').map(b => b.text || '').join('\n');
}

function human(s) {
  return s.trim() !== '' && !SKIP.some(p => s.trimStart().startsWith(p));
}

// Last human prompt in the transcript tail, and whether the CLI flagged the keyword on it.
function lastPrompt(transcriptPath) {
  const size = fs.statSync(transcriptPath).size;
  const fd = fs.openSync(transcriptPath, 'r');
  const buf = Buffer.alloc(Math.min(size, TAIL));
  try { fs.readSync(fd, buf, 0, buf.length, size - buf.length); } finally { fs.closeSync(fd); }
  let prompt = null;
  for (const line of buf.toString('utf8').split('\n')) {
    let d;
    try { d = JSON.parse(line); } catch (_) { continue; }   // first line of the tail is usually cut
    if (d.type === 'attachment') {
      const at = d.attachment || {};
      if (at.type === 'workflow_keyword_request' && prompt) prompt.keyword = true;
      else if (at.type === 'queued_command') {
        const s = textOf(at.prompt);
        if (human(s)) prompt = { text: s, keyword: false };
      }
      continue;
    }
    if (d.type !== 'user' || d.isMeta || d.isCompactSummary || d.isSidechain) continue;
    const content = (d.message || {}).content;
    if (Array.isArray(content) && content.some(b => b && b.type === 'tool_result')) continue;
    const s = textOf(content);
    if (human(s)) prompt = { text: s, keyword: false };
  }
  return prompt;
}

function shape(input) {
  let script = input.script || '';
  if (!script && input.scriptPath) { try { script = fs.readFileSync(input.scriptPath, 'utf8'); } catch (_) {} }
  const name = input.name || (script.match(/name:\s*['"]([^'"]+)['"]/) || [])[1] || '?';
  const votes = [...script.matchAll(/Array\.from\(\s*\{\s*length:\s*(\d+)/g)].map(m => +m[1]);
  return {
    name,
    agents: (script.match(/\bagent\s*\(/g) || []).length,   // literal calls, prompts included: a floor, not a count
    votes: votes.length ? Math.max(...votes) : 0,
    maps: (script.match(/\.map\s*\(/g) || []).length,
    loops: /\bwhile\s*\(/.test(script) ? 1 : 0,
  };
}

function csv(v) { return '"' + String(v).replace(/"/g, "'").replace(/\s+/g, ' ').slice(0, 120) + '"'; }

readStdin(data => {
  if (!TOOLS.includes(data.tool_name)) return;
  const input = data.tool_input || {};
  const wf = data.tool_name === 'Workflow';
  const p = data.transcript_path && fs.existsSync(data.transcript_path) ? lastPrompt(data.transcript_path) : null;
  const asked = p ? (p.keyword || REQUEST.test(p.text)) : null;   // null = no prompt found in the tail
  const w = wf ? shape(input)
    : { name: (input.subagent_type || 'general') + ': ' + (input.description || ''), agents: 1, votes: 0, maps: 0, loops: 0 };
  const gate = wf && MODE === 'ask' && asked !== true;

  // Bookkeeping only: a failed write must not change the decision.
  try {
    if (!fs.existsSync(LOG)) fs.writeFileSync(LOG, 'ts,session,tool,cwd,asked,keyword,mode,decision,name,agent_calls,max_votes,maps,loops,prompt\n');
    fs.appendFileSync(LOG, [new Date().toISOString(), sessionId(data), data.tool_name, csv(data.cwd || ''),
      asked === null ? '?' : asked ? 1 : 0, p && p.keyword ? 1 : 0, MODE, gate ? 'ask' : 'pass',
      csv(w.name), w.agents, w.votes, w.maps, w.loops, csv(p ? p.text : '')].join(',') + '\n');
  } catch (e) {
    process.stderr.write('workflow-gate.js: ' + String(e.message || e).replace(/\s+/g, ' ') + '\n');
  }

  if (!gate) return;
  process.stdout.write(JSON.stringify({
    hookSpecificOutput: {
      hookEventName: 'PreToolUse',
      permissionDecision: 'ask',
      permissionDecisionReason: S.workflowGate(w.name, w.agents, w.votes),
    }
  }));
});