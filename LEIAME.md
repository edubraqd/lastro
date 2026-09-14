# claude-context-forensics

Para onde vão os tokens no Claude Code — medido em 641 sessões reais — mais
as ferramentas para medir as suas e quatro hooks que agem sobre o que foi
encontrado.

*English: [README.md](README.md). Os relatórios estão em inglês.*

## O que foi medido

- **Leitura de cache é ~62% da conta, escrita de cache ~30%, saída ~8%.** A
  chamada média re-envia ~320k tokens; ~80k é o prefixo fixo (system prompt,
  CLAUDE.md, schemas das tools) e o resto é o histórico da conversa. Enxugar
  o CLAUDE.md mexe em ~2%. O tamanho da sessão mexe em tudo.
- **80% de toda a escrita de cache vem de poucas re-escritas grandes**, não
  do crescimento normal: um intervalo ocioso acima de 60 min (o TTL de 1h)
  quebra o cache em 93–97% das vezes; abaixo de 20 min, 1–7%. Resume e troca
  de modelo re-escrevem o histórico inteiro atrás de um prefixo compartilhado
  de 49k. Trocar o nível de esforço no meio da sessão re-escreve em 31%
  das vezes; boa parte do resto era bug do cliente que parou de reproduzir
  depois da 2.1.237.
- **O `.jsonl` da sessão infla o uso 1,7×** se você não deduplicar por
  `(message.id, requestId)` — uma linha por bloco de conteúdo, mesmo `usage`
  em todas.
- `skillOverrides` economiza 4,5% do prefixo (~2,7k tokens/chamada); skill de
  plugin ignora. `CLAUDE_CODE_COLD_COMPACT` é código morto na 2.1.270.
  Resposta em modo terso corta 8% da saída, e saída é 8% do custo.

Relatórios: [report/cache-forensics.md](report/cache-forensics.md) (aberto
como [anthropics/claude-code#94177](https://github.com/anthropics/claude-code/issues/94177)),
[report/cache-forensics-followup.md](report/cache-forensics-followup.md) e
[report/findings.md](report/findings.md) com o resto, cada item com método e n.

## Medir as suas sessões

Python 3.8+, só stdlib. Lê `~/.claude/projects/*/*.jsonl`; não escreve nada.

```bash
python tools/sessions.py                 # uso por sessão, dedup, divisão do custo
python tools/sessions.py --last 0 --min-calls 5
python tools/breaks.py                   # quebras de cache classificadas: ttl / prune / resume / ...
python tools/ttl.py --last 0             # taxa de quebra por intervalo ocioso
python tools/rewrites.py --last 0        # re-escritas sem gap: o que mudou antes do histórico
python tools/diverge.py                  # log do proxy: em cada quebra, o primeiro byte que difere da chamada anterior
```

`tools/cache-proxy.py` é um proxy local que registra o uso por chamada e
(experimental) faz um ping na API a cada 20 min ocioso para manter o cache de
1h quente. Lance por ele com `tools/wrap-cache.sh` ou `tools/wrap-cache.ps1`.
Leia o docstring antes de usar o keep-alive: cada ping custa uma leitura de
cache do contexto inteiro.

## Hooks

Node.js, sem dependência. Agem sobre os mecanismos acima, não sobre um
contador global de tokens.

| hook | evento | faz |
|---|---|---|
| `context-guard.js` | UserPromptSubmit | lê o contexto da última chamada no transcript; acima de `CONTEXT_LIMIT` (200k) avisa o modelo, todo turno, para fechar e pedir `/clear`. Grava o pico por sessão em `~/.claude/.context-peaks.json`. |
| `batch-eviction.js` | Stop | acima de `EVICTION_LIMIT` (150k), uma vez por sessão, segura o stop e faz o modelo escrever o handoff em `<cwd>/.claude/handoff-<sessão>.md`. |
| `handoff-load.js` | SessionStart | depois de `/clear` ou sessão nova, injeta o handoff mais recente (< `HANDOFF_HOURS`, 12) e instala o **canário de contexto**: uma primeira linha byte-estável (`**ctx · t<N> · ctx ok**`) que some quando a instrução caiu do contexto. |
| `read-recovery.js` | PostToolUse (Read) | quando um `Read` teve `limit`, diz ao modelo quantas linhas faltam e o offset para continuar. |

Instalar (aponta para o checkout, então `git pull` atualiza):

```bash
git clone https://github.com/edubraqd/claude-context-forensics
cd claude-context-forensics
python hooks/install.py --dry-run      # mostra o settings.json resultante
python hooks/install.py                # ~/.claude/settings.json (guarda backup)
python hooks/install.py --project .    # ou o .claude/settings.json de um projeto
python hooks/install.py --uninstall
```

Ajustes, por variável de ambiente ou em `"env"` no settings.json:
`CONTEXT_LANG=pt` (mensagens em português), `CONTEXT_LIMIT`,
`EVICTION_LIMIT`, `HANDOFF_HOURS`, `CANARY=0`, `CANARY_NAME`.

Por que handoff em arquivo e não `/compact`: histórico podado com resumo curto
do que foi feito venceu tanto o histórico inteiro quanto o resumo do histórico
inteiro em custo, com acurácia igual ou melhor, no "Less Context, Better
Agents" da Microsoft (arXiv 2606.10209). O canário é do
[JuliusBrussee/skills](https://github.com/JuliusBrussee/skills); a evicção em
lote, do TokenPilot (arXiv 2606.17016). Ver findings §9.

Teste: `python tests/test_hooks.py` (precisa de `node`; usa um diretório de
configuração temporário, não toca em `~/.claude`).

## Ressalvas

Um usuário, uma máquina, sessões longas com a janela de 1M ligada. As
proporções vão ser outras para você; os mecanismos (TTL, prune, resume,
duplicação do jsonl) não. O código do Claude Code não é público: o
comportamento do "microcompact" é inferido dos deltas de uso e de strings do
binário. Os valores em dólar são equivalentes de API a preço de tabela;
assinatura é contabilizada de outro jeito.

## Licença

MIT.
