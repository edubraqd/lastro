#!/usr/bin/env python3
"""Register the hooks in ~/.claude/settings.json (or a project's .claude/settings.json).

The hooks are referenced in place (absolute path into this checkout), so a
`git pull` updates them. Existing hooks from other tools are kept; only
entries that run one of our hook scripts (from any checkout) are added or removed.

    python hooks/install.py --dry-run          # show the resulting settings, write nothing
    python hooks/install.py                    # install into ~/.claude/settings.json
    python hooks/install.py --project .        # into <dir>/.claude/settings.json instead
    python hooks/install.py --uninstall
    python hooks/install.py --only context-guard,handoff-load   # add or refresh just these
    python hooks/install.py --only read-recovery --uninstall    # remove just this one

Environment knobs (put them under "env" in settings.json or export them):
  CONTEXT_LANG=pt      Portuguese strings (default: English)
  CONTEXT_LIMIT=200000 context-guard threshold (tokens)
  EVICTION_LIMIT=150000 batch-eviction threshold (tokens)
  HANDOFF_HOURS=72     max age of a handoff to re-inject; 0 turns the handoff off (canary stays)
  CANARY=0             disable the context canary
  CANARY_NAME=Lastro   name shown in the canary line
"""
import argparse
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HOOKS = {
    "context-guard": ("UserPromptSubmit", None, "Measuring context..."),
    "batch-eviction": ("Stop", None, "Checking context for eviction..."),
    "handoff-load": ("SessionStart", "startup|clear", "Loading handoff..."),
    "read-recovery": ("PostToolUse", "Read", "Checking Read cut..."),
}


def node_path():
    for cand in ("node", "node.exe"):
        p = shutil.which(cand)
        if p:
            return p
    for p in (r"C:\Program Files\nodejs\node.exe", "/usr/local/bin/node", "/opt/homebrew/bin/node"):
        if os.path.exists(p):
            return p
    sys.exit("node not found on PATH; install Node.js or pass --node <path>")


def quote(p):
    """Always quoted, forward slashes: the command runs through a POSIX shell even
    on Windows, where a bare backslash path loses its separators."""
    return '"' + p.replace("\\", "/") + '"'


def command_for(name, node):
    return quote(node) + " " + quote(os.path.join(HERE, name + ".js"))


def is_ours(hook, names):
    """Match by shape (.../hooks/<name>.js), not by this checkout's path: a moved
    or second checkout must still find and replace the old entries."""
    pat = r"[\\/]hooks[\\/](" + "|".join(re.escape(n) for n in names) + r")\.js\"?$"
    # IGNORECASE: `python HOOKS/install.py` on a case-insensitive filesystem registers the
    # path as typed; the pattern is anchored at the end, so the flag only widens which case
    # of the same path is accepted, never what shape
    return re.search(pat, hook.get("command") or "", re.IGNORECASE) is not None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", help="install into <dir>/.claude/settings.json instead of the user file")
    ap.add_argument("--only", help="comma-separated subset of: " + ", ".join(HOOKS))
    ap.add_argument("--node", help="path to the node binary")
    ap.add_argument("--uninstall", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.project:
        settings_path = os.path.join(os.path.abspath(args.project), ".claude", "settings.json")
    else:
        claude_dir = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
        settings_path = os.path.join(claude_dir, "settings.json")

    settings = {}
    if os.path.exists(settings_path):
        with open(settings_path, encoding="utf-8") as f:
            settings = json.load(f)
    hooks = settings.setdefault("hooks", {})

    wanted = [n.strip() for n in args.only.split(",")] if args.only else list(HOOKS)
    for name in wanted:
        if name not in HOOKS:
            sys.exit("unknown hook: " + name)

    # the backup is the file before Lastro touched it: decided on ALL our hooks, not only the
    # wanted ones, so a second --only does not overwrite the first backup
    had_ours = any(is_ours(h, list(HOOKS)) for gs in hooks.values() for g in gs for h in g.get("hooks", []))
    backup = os.path.exists(settings_path) and not had_ours

    # drop our entries for the wanted hooks (whatever checkout registered them), then re-add them
    removed = 0
    for event, groups in list(hooks.items()):
        for g in groups:
            kept = [h for h in g.get("hooks", []) if not is_ours(h, wanted)]
            removed += len(g.get("hooks", [])) - len(kept)
            g["hooks"] = kept
        hooks[event] = [g for g in groups if g.get("hooks")]
        if not hooks[event]:
            del hooks[event]

    if not args.uninstall:
        node = args.node or node_path()
        for name in wanted:
            event, matcher, status = HOOKS[name]
            entry = {"type": "command", "command": command_for(name, node), "timeout": 5, "statusMessage": status}
            group = {"hooks": [entry]}
            if matcher:
                group["matcher"] = matcher
            hooks.setdefault(event, []).append(group)

    if not hooks:
        del settings["hooks"]

    out = json.dumps(settings, indent=2, ensure_ascii=False)
    # before the dry run: a real --uninstall with nothing of ours writes nothing, so the
    # dry run must not say "would write"
    if args.uninstall and not removed:
        print("removed 0 entries: nothing of ours in " + settings_path, file=sys.stderr)
        return
    if args.dry_run:
        print(out)
        print("\n(dry run) would write", settings_path, file=sys.stderr)
        return
    os.makedirs(os.path.dirname(settings_path), exist_ok=True)
    if backup:
        shutil.copy2(settings_path, settings_path + ".bak")
    with open(settings_path, "w", encoding="utf-8") as f:
        f.write(out + "\n")
    if args.uninstall:
        print("removed %d entries from %s" % (removed, settings_path))
    else:
        print("installed into " + settings_path + (" (backup: settings.json.bak)" if backup else ""))


if __name__ == "__main__":
    main()
