"""Synthetic Claude Code transcripts for the tool tests.

Builds a fake CLAUDE_CONFIG_DIR with one project and two transcripts:

  s1.jsonl  8 API calls, each written twice (one line per content block,
            same usage on both, which is what Claude Code does), with one
            break of each kind: ttl (88 min gap), compact (summary line
            between the calls), resume (model changed).
  s2.jsonl  a resume copy of s1 (every line duplicated) plus one new call.
            Processed after s1, it must contribute only that one call.

build_side() writes a separate tree with one transcript, s3.jsonl: three
main calls, a burst of three `isSidechain` (subagent) calls, then the main
thread resuming from its own cache. It lives apart so the s1/s2 numbers
never move.

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

# subagent calls interleaved with the main thread: pairwise tools must skip
# them, per-session totals must keep them (they are billed)
SIDE_MAIN = [
    ("2026-09-14T10:00:00.000Z", MODEL, 5, 100000, 0, 50),
    ("2026-09-14T10:01:00.000Z", MODEL, 5, 1000, 100000, 50),
    ("2026-09-14T10:02:00.000Z", MODEL, 5, 1000, 101000, 50),
]
SIDE_SUB = [
    ("2026-09-14T10:02:10.000Z", "claude-sonnet-5", 5, 50000, 0, 50),   # cold start of another prefix
    ("2026-09-14T10:02:20.000Z", "claude-sonnet-5", 5, 500, 50000, 50),
    ("2026-09-14T10:02:30.000Z", "claude-sonnet-5", 5, 500, 50500, 50),
]
SIDE_BACK = ("2026-09-14T10:03:00.000Z", MODEL, 5, 2000, 102000, 50)    # main resumes from its cache
SIDE_SUB_CW = sum(c[3] for c in SIDE_SUB)                              # 51000, all 5m writes
SIDE_CW = sum(c[3] for c in SIDE_MAIN) + SIDE_SUB_CW + SIDE_BACK[3]    # 155000


def _lines(calls, sid, start=0, side=None):
    """side=None keeps the s1/s2 lines byte-identical; a bool adds isSidechain and the TTL buckets."""
    out = []
    for i, (t, model, inp, cw, cr, outp) in enumerate(calls, start):
        msg = {"id": "msg_%d" % i, "model": model, "role": "assistant",
               "usage": {"input_tokens": inp, "cache_creation_input_tokens": cw,
                         "cache_read_input_tokens": cr, "output_tokens": outp}}
        base = {"type": "assistant", "requestId": "req_%d" % i, "timestamp": t,
                "version": VERSION, "entrypoint": "cli", "sessionId": sid}
        if side is not None:
            base["isSidechain"] = side
            msg["usage"]["cache_creation"] = {"ephemeral_5m_input_tokens": cw if side else 0,
                                              "ephemeral_1h_input_tokens": 0 if side else cw}
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
    # transcripts() orders by mtime, then size on a tie: the original must come first
    os.utime(p1, (1700000000, 1700000000))
    os.utime(p2, (1700000100, 1700000100))
    return cfg, p1, p2


def build_side(root):
    """Write the sidechain tree under root. Returns (cfg_dir, s3_path)."""
    cfg = os.path.join(root, "claude")
    proj = os.path.join(cfg, "projects", "D--proj-b")
    os.makedirs(proj)
    lines = (_lines(SIDE_MAIN, "s3", side=False)
             + _lines(SIDE_SUB, "s3", start=len(SIDE_MAIN), side=True)
             + _lines([SIDE_BACK], "s3", start=len(SIDE_MAIN) + len(SIDE_SUB), side=False))
    p3 = os.path.join(proj, "s3.jsonl")
    with open(p3, "w", encoding="utf-8") as fh:
        for l in lines:
            fh.write(json.dumps(l, ensure_ascii=False) + "\n")
    return cfg, p3
