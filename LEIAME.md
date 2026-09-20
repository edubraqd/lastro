# Lastro

**O recibo por trás da fatura do Claude Code — e o freio que evita a parte
mais cara dela.**

*English: [README.md](README.md).*

## O que faz você gastar mais do que precisa

Medido em 674 sessões reais de um usuário (não é estimativa):

1. **Cada mensagem reenvia a conversa inteira.** Numa sessão longa, a chamada
   média reenvia ~320 mil tokens. Ler esse histórico de novo é **62% da
   conta**. O que você digita é uma fração; o que pesa é tudo que veio antes.
2. **Parar mais de 1 hora e voltar custa uma reconstrução.** O cache dura
   1 hora. Intervalo maior que isso obriga o Claude a reescrever a conversa
   inteira em **93 a 97% das vezes**; intervalo menor que 20 minutos, só 1 a
   7%. Essas reescritas são **80% de tudo que se gasta com escrita de cache**.
   Trocar de modelo ou retomar uma sessão antiga (`--resume`) faz o mesmo.
3. **Deixar a sessão crescer sem limpar.** O tamanho da sessão é o que mais
   mexe na conta: a 200 mil tokens, cada resposta reenvia 200 mil tokens. E
   instrução dada no começo pode cair fora do que o Claude ainda enxerga — o
   Lastro mede isso, não adivinha (a linha do topo, abaixo).

O que resolve é simples e ninguém faz na hora: **antes de sair, salvar um
resumo do que foi feito e limpar a conversa (`/clear`)**. Ao voltar, o Claude
lê o resumo em vez de reler tudo. Acima de 150 mil tokens o Lastro faz isso
sozinho; abaixo disso, antes de sair, peça ao Claude para escrever o handoff
em `.claude/handoff-<sessão>.md` (a cláusula TRIP da linha do canário traz o
caminho exato; com `CANARY=0` essa linha não existe, então nomeie o arquivo
você mesmo: `handoff-` + os 8 primeiros hex do id da sessão) e dê `/clear`.

## O que o Lastro faz na sua tela

Quatro automações pequenas (hooks) que rodam dentro do Claude Code:

| quando | o que você vê |
|---|---|
| a conversa passa de 150 mil tokens | o Claude escreve um resumo do trabalho em `.claude/handoff-<sessão>.md` antes de parar. O essencial fica (umas 60 linhas); o transcript completo continua em `~/.claude/projects` e a sessão nova recebe o caminho dele quando o resumo é carregado. |
| passa de 200 mil | em toda resposta o Claude avisa que está pesado e pede para você dar `/clear`. |
| você dá `/clear` ou abre sessão nova | o resumo mais novo que ainda dá para carregar — escrito por uma sessão desta máquina, com menos de 72 h (`HANDOFF_HOURS`), nunca carregado antes — entra sozinho e o trabalho retoma de onde parou. Handoff que chegou por `git clone` ou cópia é pulado, e não esconde um mais velho que seja seu. Se existe um resumo que não pôde ser carregado, o Claude é avisado disso e do motivo, e não o lê sem você pedir. |
| toda resposta, depois disso | a primeira linha é `**Lastro · t3 · ctx ok**`: o número sobe a cada resposta e `ok / aging / thin` diz se o Claude ainda lembra das decisões. Se a linha **sumir**, ele já esqueceu — hora de `/clear`. |
| o Claude lê um arquivo pela metade | recebe aviso de quantas linhas faltam, para não reler do zero. |

Nenhuma delas manda dado para fora do seu computador.

## Instalar (3 passos)

Precisa de [Node.js](https://nodejs.org) e [Python 3.8+](https://www.python.org)
instalados — os dois são "baixar, avançar, avançar".

```bash
git clone https://github.com/edubraqd/lastro
```
```bash
cd lastro
```
```bash
python hooks/install.py
```

Pronto. Feche e abra o Claude Code. Para mensagens em português e seu nome na
linha do topo, ponha no `~/.claude/settings.json`:

```json
"env": { "CONTEXT_LANG": "pt", "CANARY_NAME": "SeuNome" }
```

Desinstalar: `python hooks/install.py --uninstall` (com `--project .` se instalou
num projeto). Ficam para trás `~/.claude/.context-peaks.json`, os
`.claude/handoff-*.md` de cada projeto e o `settings.json.bak` (o seu settings
de antes da primeira instalação); apague à mão para zerar. Ver o que seria
alterado antes: `--dry-run`.

## Quanto você gastou

```bash
python tools/ledger.py
```

Lê os registros que o Claude Code já guarda no seu computador
(`~/.claude/projects`) e imprime, em dólar de tabela da API, quanto foi
histórico, quanto foi reconstrução por intervalo, quanto cada hábito acima
custou. Não escreve nada e não manda nada para fora. Em assinatura o número é
cota, não dinheiro — mas a proporção é a mesma.

---

## Para quem é técnico

Os relatórios e as páginas de apoio estão em inglês.

| comece por aqui | |
|---|---|
| [SAVINGS.md](SAVINGS.md) | cada alavanca, a evidência dela e o US$ em logs reais — teto marcado como teto |
| [AUDIT.md](AUDIT.md) | de onde sai cada número e como refazê-lo a partir dos transcripts crus |
| [AGENTS.md](AGENTS.md) | o resumo operacional para um agente de código: oito regras, um bloco para colar |
| [report/](report/) | os relatórios, com método e n |
| [experiments/](experiments/) | o harness do A/B, com as rodadas cruas |

## O que foi medido

- **Leitura de cache é ~62% da conta, escrita de cache ~30%, saída ~8%.** A
  chamada média re-envia ~320k tokens; ~80k é o prefixo fixo (system prompt,
  CLAUDE.md, schemas das tools) e o resto é o histórico da conversa. Enxugar
  o CLAUDE.md mexe em ~0,2% por 1k tokens. O tamanho da sessão mexe em tudo.
- **80% de toda a escrita de cache vem de poucas re-escritas grandes**, não
  do crescimento normal: um intervalo ocioso acima de 60 min (o TTL de 1h)
  quebra o cache em 93–97% das vezes; abaixo de 20 min, 1–7%. Resume e troca
  de modelo re-escrevem o histórico inteiro atrás de um prefixo compartilhado
  de 49k. Trocar o nível de esforço no meio da sessão re-escreve em 31%
  das vezes. Metade dos 80% era bug do cliente que parou de reproduzir depois
  da 2.1.237.
- **Um hit de cache renova o TTL de 1h, e mesmo assim um pinger cego de
  keep-alive perde dinheiro** (−0,8% sobre os intervalos reais: a maioria dos
  intervalos longos é a madrugada). Handoff + `/clear` antes de sair é a
  versão dessa alavanca que paga.
- **Uma configuração completa (CLAUDE.md + memória + hooks + overrides) acertou
  100% contra 92%, fez 40% menos chamadas e custou US$0,10 a mais por sessão
  de uma tarefa** — o prefixo de 21k que ela escreve a cada sessão nova, e que
  nunca é servido do cache de outra sessão. Equilíbrio em ~3 tarefas por sessão.
- **Instalado de uma vez, o pacote cortou a conta real em 45% por chamada e
  58% por dia** nos cinco dias depois de 14/09 contra os catorze antes
  (contexto por chamada 262k → 134k, chamadas acima de 200k 64% → 13%,
  autocompact 17 → 0). Degrau no dia da instalação com chamadas/dia estáveis;
  quase tudo é o cap + handoff, não settings.
  [report/usage-real-2026-09-17.md](report/usage-real-2026-09-17.md) (inglês).
- **O `.jsonl` da sessão infla o uso 1,7×** se você não deduplicar por
  `(message.id, requestId)` — uma linha por bloco de conteúdo, mesmo `usage`
  em todas.
- `skillOverrides` economiza 4,5% do prefixo (~2,7k tokens/chamada); skill de
  plugin ignora. `CLAUDE_CODE_COLD_COMPACT` é código morto na 2.1.270. A
  conversa principal é cache de 1h em 100% das escritas e subagente é 5m em
  100%; os ajustes de TTL não fazem nada útil aqui. Resposta em modo terso
  corta 8% da saída, e saída é 8% do custo.

Relatórios: [report/cache-forensics.md](report/cache-forensics.md) (aberto
como [anthropics/claude-code#94177](https://github.com/anthropics/claude-code/issues/94177)),
[report/cache-forensics-followup.md](report/cache-forensics-followup.md),
[report/findings.md](report/findings.md) (o resto, cada item com método e n) e
[report/ab-config-vs-bare.md](report/ab-config-vs-bare.md) (o A/B).

## Medir as suas sessões

Python 3.8+, só stdlib. Lê `~/.claude/projects/*/*.jsonl` (ou
`$CLAUDE_CONFIG_DIR/projects`); não escreve nada.

```bash
python tools/ledger.py                   # a tabela do SAVINGS.md nos seus transcripts
python tools/before_after.py --split 2026-09-14 --daily   # uma mudança no dia X mexeu na conta? (report/usage-real-2026-09-17.md)
python tools/sessions.py                 # uso por sessão, dedup, divisão do custo
python tools/sessions.py --last 0 --min-calls 5
python tools/breaks.py                   # quebras de cache classificadas: ttl / prune / resume / ...
python tools/ttl.py --last 0             # taxa de quebra por intervalo ocioso
python tools/rewrites.py --last 0        # re-escritas sem gap: o que mudou antes do histórico
python tools/first_call.py               # 1ª chamada de cada sessão: o que um início quente lê de outras sessões (anthropics/claude-code#93499; o nosso #94417 foi fechado como duplicata dele)
python tools/diverge.py                  # log do proxy: em cada quebra, o primeiro byte que difere da chamada anterior
python tools/issues.py --top 40          # GitHub: issues do claude-code sobre cache/contexto/custo, por reações (precisa de GITHUB_TOKEN ou gh)
```

`tools/cache-proxy.py` é um proxy local que registra o uso por chamada e
guarda todo corpo de requisição (para o `diverge.py`). O ping de keep-alive
dele está medido renovando o TTL e medido dando prejuízo quando roda cego —
leia o findings §3 antes de ligar. Lance por ele com `tools/wrap-cache.sh`
ou `tools/wrap-cache.ps1`.

## Rodar o A/B no seu projeto

```bash
cd experiments/ab-config-vs-bare
cp tasks.example.py tasks.py             # 5-8 tarefas do seu projeto, com oráculo
python run.py --project /caminho/do/repo --reps 3 --workers 3   # ~US$12 de cota para 48 rodadas em Opus
python judge.py && python analyze.py && python decomp.py
```

O [README do experimento](experiments/ab-config-vs-bare/README.md) explica
as escolhas de desenho; `data/` guarda as 48 rodadas de 14/09/2026.

## Hooks

Node.js, sem dependência. Agem sobre os mecanismos acima, não sobre um
contador global de tokens.

| hook | evento | faz |
|---|---|---|
| `context-guard.js` | UserPromptSubmit | lê o contexto da última chamada no transcript; acima de `CONTEXT_LIMIT` (200k) avisa o modelo, todo turno, para fechar e pedir `/clear`. Logo depois de `/compact` o tamanho é desconhecido até a chamada seguinte (a contagem de tokens do resumo não é o contexto), então ele fica calado nesse prompt. Grava o pico por sessão em `~/.claude/.context-peaks.json`; um arquivo de picos que não consegue ler ou gravar fica intocado (o aviso sai do mesmo jeito; a falha vira uma linha no stderr). |
| `batch-eviction.js` | Stop | acima de `EVICTION_LIMIT` (150k), uma vez por sessão, segura o stop e faz o modelo escrever o handoff em `<cwd>/.claude/handoff-<sessão>.md`. |
| `handoff-load.js` | SessionStart (`startup\|clear`) | depois de `/clear` ou sessão nova, percorre os handoffs do mais novo ao mais velho e injeta o primeiro que consegue carregar (< `HANDOFF_HOURS`, 72; escrito por sessão que rodou nesta máquina; nunca carregado antes). Arquivo estrangeiro ou já carregado não esconde um mais velho que seja seu; arquivo que existe mas não foi carregado é nomeado ao modelo, com o motivo. A carga é registrada (pelo mtime do arquivo, no `.context-peaks.json`) antes de o texto entrar: se a marca não grava, nada é injetado e o próximo `/clear` tenta de novo. O texto entra como arquivo `<handoff>` (os primeiros 12000 chars; uma nota depois do bloco dá o caminho do resto) que o modelo deve conferir contra a árvore de trabalho. Depois instala o **canário de contexto**: uma primeira linha byte-estável (`**Lastro · t<N> · ctx ok**`) que some quando a instrução caiu do contexto; o canário nunca depende do handoff. |
| `read-recovery.js` | PostToolUse (Read) | quando um `Read` teve `limit`, diz ao modelo quantas linhas faltam e o offset para continuar. |

Instalar (aponta para o checkout, então `git pull` atualiza):

```bash
git clone https://github.com/edubraqd/lastro
cd lastro
python hooks/install.py --dry-run      # mostra o settings.json resultante
python hooks/install.py                # ~/.claude/settings.json (settings.json.bak = o arquivo de antes do Lastro; reinstalar não o sobrescreve)
python hooks/install.py --project .    # ou o .claude/settings.json de um projeto
python hooks/install.py --uninstall [--project .]
```

Ajustes, por variável de ambiente ou em `"env"` no settings.json:
`CONTEXT_LANG=pt` (mensagens em português), `CONTEXT_LIMIT`,
`EVICTION_LIMIT`, `HANDOFF_HOURS`, `CANARY=0` (também tira o único lugar em
que o modelo recebe o caminho do handoff abaixo de 150 mil), `CANARY_NAME`.

Por que handoff em arquivo e não `/compact`: histórico podado com resumo curto
do que foi feito venceu tanto o histórico inteiro quanto o resumo do histórico
inteiro em custo, com acurácia igual ou melhor, no "Less Context, Better
Agents" da Microsoft (arXiv 2606.10209). O canário é do
[JuliusBrussee/skills](https://github.com/JuliusBrussee/skills); a evicção em
lote, do TokenPilot (arXiv 2606.17016). Ver findings §11.

Um custo a conhecer: hook de `UserPromptSubmit` que devolve `additionalContext`
correlaciona com re-escrita completa do prefixo em 0,8% dos turnos de usuário
contra 0,06% sem (versões atuais). O `context-guard.js` só fala acima do
limite por isso.

## Testes

```bash
python -m unittest discover -s tests -v
```

`tests/test_tools.py` roda cada ferramenta contra um transcript sintético
(`tests/fixture.py`: blocos de conteúdo duplicados, uma cópia de resume, uma
quebra de cache de cada tipo) e confere o dedup, o classificador e os números
que cada uma imprime — inclusive em console `cp1252`. `tests/test_hooks.py`
roda os quatro hooks e o instalador (precisa de `node`). Os dois usam um
`CLAUDE_CONFIG_DIR` temporário e não tocam em `~/.claude`. O CI roda a suíte
em Ubuntu e Windows, Python 3.8 e 3.12.

## Ressalvas

Um usuário, uma máquina, sessões longas com a janela de 1M ligada. As
proporções vão ser outras para você; os mecanismos (TTL, prune, resume,
duplicação do jsonl) não. O código do Claude Code não é público: o
comportamento do "microcompact" é inferido dos deltas de uso e de strings do
binário. Os valores em dólar são equivalentes de API a preço de tabela; em
assinatura são cota, não dinheiro. O A/B tem n = 3 por célula em um projeto:
dá o sinal de cada linha, não o tamanho do efeito para você.

## Licença

MIT.
