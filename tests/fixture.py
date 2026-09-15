"""Synthetic Claude Code transcripts for the tool tests.

Builds a fake CLAUDE_CONFIG_DIR with one project and two transcripts:

  s1.jsonl  8 API calls, each written twice (one line per content block,
            same usage on both, which is what Claude Code does), with one
            break of each kind: ttl (88 min gap), compact (summary line
            between the calls), resume (model changed).
  s2.jsonl  a resume copy of s1 (every line duplicated) plus one new call.
            Processed after s1, it must contribute only that one call.

Every number below is referenced by tests/test_tools.py; change both.
"""
import json
import os

MODEL = "claude-opus-5"
VERSION = "2.1.272"
FIRST_PROMPT = "first prompt: café"   # non-ASCII on purpose (Windows console encoding)

# (timestamp, model, input, cache_creation, cache_read, output)
S1_CALLS = [
    ("2026-09-14T10:00:00.000Z", MODEL, 5, 80000, 0, 50),        # cold start
    ("2026-09-14T10:01:00.000Z", MODEL, 5, 2000, 85000, 50),
    ("2026-09-14T10:02:00.000Z", MODEL, 5, 1000, 87000, 50),
    ("2026-09-14T11:30:00.000Z", MODEL, 5, 88000, 0, 50),        # ttl: 88 min gap
    ("2026-09-14T11:31:00.000Z", MODEL, 5, 500, 88000, 50),
    ("2026-09-14T11:33:00.000Z", MODEL, 5, 30000, 40000, 50),    # compact: summary at 11:32
    ("2026-09-14T11:34:00.000Z", MODEL, 5, 500, 70000, 50),
    ("2026-09-14T11:35:00.000Z", "claude-sonnet-5", 5, 60000, 0, 50),  # resume: model changed
]
S2_EXTRA = ("2026-09-14T12:00:00.000Z", "claude-sonnet-5", 5, 1000, 130000, 50)
COMPACT_TS = "2026-09-14T11:32:00.000Z"

S1_CACHE_CREATION = sum(c[3] for c in S1_CALLS)   # 262000


def _lines(calls, sid, start=0):
    out = []
    for i, (t, model, inp, cw, cr, outp) in enumerate(calls, start):
        msg = {"id": "msg_%d" % i, "model": model, "role": "assistant",
               "usage": {"input_tokens": inp, "cache_creation_input_tokens": cw,
                         "cache_read_input_tokens": cr, "output_tokens": outp}}
        base = {"type": "assistant", "requestId": "req_%d" % i, "timestamp": t,
                "version": VERSION, "entrypoint": "cli", "sessionId": sid}
        out.append({**base, "message": {**msg, "content": [{"type": "text", "text": "x"}]}})
        out.append({**base, "message": {**msg, "content": [{"type": "tool_use", "name": "Bash", "input": {}}]}})
    return out


def build(root):
    """Write the tree under root (a fresh temp dir). Returns (cfg_dir, s1_path, s2_path)."""
    cfg = os.path.join(root, "claude")
    proj = os.path.join(cfg, "projects", "D--proj-a")
    os.makedirs(proj)
    s1 = _lines(S1_CALLS, "s1")
    # a compact summary sits between call 4 and call 5
    s1.insert(2 * 5, {"type": "user", "isCompactSummary": True, "timestamp": COMPACT_TS,
                      "message": {"role": "user", "content": "summary"}})
    s1.insert(0, {"type": "user", "timestamp": "2026-09-14T09:59:59.000Z",
                  "message": {"role": "user", "content": FIRST_PROMPT}})
    s2 = [dict(l, sessionId="s2") for l in s1] + _lines([S2_EXTRA], "s2", start=len(S1_CALLS))
    p1 = os.path.join(proj, "s1.jsonl")
    p2 = os.path.join(proj, "s2.jsonl")
    for p, lines in ((p1, s1), (p2, s2)):
        with open(p, "w", encoding="utf-8") as fh:
            for l in lines:
                fh.write(json.dumps(l, ensure_ascii=False) + "\n")
    # transcripts() orders by mtime: the original must come first
    os.utime(p1, (1700000000, 1700000000))
    os.utime(p2, (1700000100, 1700000100))
    return cfg, p1, p2
