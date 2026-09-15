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


def utf8_stdout():
    """Transcripts are UTF-8; a cp1252 console would raise on the first accent."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


utf8_stdout()
