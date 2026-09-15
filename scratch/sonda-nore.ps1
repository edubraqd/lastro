# Sonda: CLAUDE_CODE_TOTAL_TOKENS_REMINDER=off tira o bloco <total_tokens> do transcript em `claude -p`?
# Rodar de D:\claude-context-forensics (o cwd decide a pasta do transcript). Haiku, 2 sessoes, centavos.
$BIN = "C:\Users\eduar\.npm-global\node_modules\@anthropic-ai\claude-code\bin\claude.exe"
$env:CANARY = "0"; $env:CANARIO = "0"
foreach ($mode in "default", "off") {
    if ($mode -eq "off") { $env:CLAUDE_CODE_TOTAL_TOKENS_REMINDER = "off" }
    else { Remove-Item Env:CLAUDE_CODE_TOTAL_TOKENS_REMINDER -ErrorAction SilentlyContinue }
    $out = & $BIN -p "Rode 'ls experiments' com a ferramenta Bash e depois responda so 'feito'." `
        --model claude-haiku-4-5-20251001 --output-format json --strict-mcp-config `
        --dangerously-skip-permissions --max-turns 5 --setting-sources user,project,local 2>$null
    $sid = ($out | ConvertFrom-Json).session_id
    Start-Sleep 2
    $f = "$HOME\.claude\projects\D--claude-context-forensics\$sid.jsonl"
    $n = (Select-String -Path $f -Pattern 'total_tokens>' | Measure-Object).Count
    "$mode sid=$sid total_tokens=$n lines=$((Get-Content $f).Count)"
}
Remove-Item Env:CLAUDE_CODE_TOTAL_TOKENS_REMINDER -ErrorAction SilentlyContinue
