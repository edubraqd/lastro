#!/usr/bin/env bash
# Launch Claude Code through tools/cache-proxy.py (usage log + cache keep-alive).
# Starts the proxy if it is not up. Usage: tools/wrap-cache.sh [claude args]
port="${CACHE_PROXY_PORT:-8790}"
here="$(cd "$(dirname "$0")" && pwd)"
if ! curl -fs "http://127.0.0.1:$port/_status" >/dev/null 2>&1; then
  nohup python3 "$here/cache-proxy.py" >/dev/null 2>&1 &
  sleep 2
fi
export ANTHROPIC_BASE_URL="http://127.0.0.1:$port"
# Without this Claude Code treats the proxy as a third-party endpoint and drops the 1M window.
export _CLAUDE_CODE_ASSUME_FIRST_PARTY_BASE_URL=1
exec claude "$@"
