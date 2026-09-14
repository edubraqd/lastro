# Launch Claude Code through tools/cache-proxy.py (usage log + cache keep-alive).
# Starts the proxy if it is not up. Usage: pwsh tools/wrap-cache.ps1 [claude args]
$port = if ($env:CACHE_PROXY_PORT) { $env:CACHE_PROXY_PORT } else { 8790 }
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$alive = try { (Invoke-WebRequest -Uri "http://127.0.0.1:$port/_status" -TimeoutSec 2 -UseBasicParsing).StatusCode -eq 200 } catch { $false }
if (-not $alive) {
    Start-Process -WindowStyle Hidden python -ArgumentList "`"$here\cache-proxy.py`""
    Start-Sleep -Seconds 2
}
$env:ANTHROPIC_BASE_URL = "http://127.0.0.1:$port"
# Without this Claude Code treats the proxy as a third-party endpoint and drops the 1M window.
$env:_CLAUDE_CODE_ASSUME_FIRST_PARTY_BASE_URL = "1"
claude @args
