"""Shared bits for the tools: where the transcripts live, timestamp parsing,
and a stdout that survives a Windows console.

Every tool imports this instead of carrying its own copy.
"""
import os
import sys
from datetime import datetime

# Claude Code honours CLAUDE_CONFIG_DIR; so do we (and so do the tests).
CLAUDE_DIR = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
PROJECTS = os.path.join(CLAUDE_DIR, "projects")


def ts(s):
    """Transcript timestamp ('2026-09-14T10:00:00.000Z') -> aware datetime."""
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


# API list prices, US$ per M tokens: (input, 5m write, 1h write, cache read, output).
# First family that is a substring of message.model wins, so a longer id goes before its prefix
# (sonnet-5-5 before sonnet-5). Reads are no longer 0.1x everywhere: 0.05x on Opus/Sonnet 5.5,
# 0.025x on Fable/Mythos 5.1. Sonnet 5.5 reads were $0.20 before changelog 2.1.296.
MODEL_PRICES = (
    ("fable-5-1", (10, 12.5, 20, 0.25, 50)), ("mythos-5-1", (10, 12.5, 20, 0.25, 50)),
    ("fable-5", (10, 12.5, 20, 1.0, 50)), ("mythos-5", (10, 12.5, 20, 1.0, 50)),
    ("opus-5-5", (4, 5, 8, 0.20, 20)),
    ("opus-4-1", (15, 18.75, 30, 1.5, 75)),
    ("opus", (5, 6.25, 10, 0.5, 25)),
    ("sonnet-5-5", (2, 2.5, 4, 0.10, 10)), ("sonnet-5", (2, 2.5, 4, 0.20, 10)),
    ("sonnet", (3, 3.75, 6, 0.30, 15)),
    ("haiku-5-5", (0.10, 0.125, 0.20, 0.01, 0.50)),
    ("haiku", (1, 1.25, 2, 0.10, 5)),
)
DEFAULT_PRICES = (5, 6.25, 10, 0.5, 25)   # Opus 5: unknown and <synthetic> models


def sheet(model, prompt_tokens=0):
    """US$ per token for one call of `model`. Haiku 5.5 costs 5x when the prompt is over 100k."""
    m = model or ""
    i, w5, w1, r, o = next((p for fam, p in MODEL_PRICES if fam in m), DEFAULT_PRICES)
    k = 5 if "haiku-5-5" in m and prompt_tokens > 100000 else 1
    return {"input": k * i / 1e6, "cw5m": k * w5 / 1e6, "cw1h": k * w1 / 1e6, "cr": k * r / 1e6, "out": k * o / 1e6}


def prices(per_m_input):
    """One flat sheet (--price-input): input P, cache read 0.1 P, 1h write 2 P, 5m write 1.25 P, output 5 P."""
    P = per_m_input / 1e6
    return {"input": P, "cr": 0.1 * P, "cw1h": 2.0 * P, "cw5m": 1.25 * P, "out": 5.0 * P}


def utf8_stdout():
    """Transcripts are UTF-8; a cp1252 console would raise on the first accent."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


utf8_stdout()
