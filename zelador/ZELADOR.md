# Zelador: missão que atravessa o /clear no app desktop

**Estado (09/11/2026): experimental.** Unidade verde (vigia 9 testes, gate e armar 6, instalador 2). O ciclo
ponta a ponta rodou uma vez, com missão mecânica (1 cobaia Sonnet 5.5, 3 clears, `--min-ctx 0`): 4 gerações
encadeadas sem ninguém colar nada, os 3 clears liberados pelo `allow` do gate. O `/missao` passou a armar
por hook (`mission-arm`), medido na CLI do app sem modelo e numa sessão do app com modelo (n = 1): texto do
teclado ao arquivo byte a byte, e o modelo pulou o passo de armar. Uma segunda rodada, de 1 clear, pôs trabalho
real na geração aberta pelo `segue`: commit, leitura de rede e apagar um arquivo da própria missão, os 4 comandos
aceitos (n = 1 de cada). Ainda sem medição: missão real (contexto cheio, handoff de verdade, clear pedido pela
guarda).

## O problema

No app desktop, `clear_session("self")` para a CLI da sessão ~1,6 s depois do fim do turno, e nada sobe
sem mensagem nova (medido 08/11/2026). Uma sessão não consegue se limpar e seguir sozinha. O zelador é
uma segunda sessão que manda essa mensagem.

## Peças

| peça | roda em | faz |
|---|---|---|
| `zelador/missao.py` | sessão de trabalho | arma, conclui e mostra a missão (`~/.claude/zelador/missoes/<host>.json`) |
| `hooks/clear-gate.js` | PreToolUse da sessão de trabalho | só com missão armada e `session_id: "self"`: nega sem vigia vivo, sem handoff desta geração, no teto de ciclos ou abaixo do contexto mínimo; senão grava o pedido e libera |
| `zelador/vigia.py` | background da zeladora | espera a CLI do pedido sair e termina com código 0; o fim dele acorda a zeladora |
| `/zelador` | sessão zeladora | sobe o vigia; quando ele termina com 0, sobe de novo e manda `segue` |
| `hooks/mission-arm.js` | UserPromptExpansion da sessão de trabalho, só no `/missao` | pega o texto como foi digitado e passa ao `missao.py armar` antes de o modelo ler o comando; avisa o modelo que já armou |
| `/missao <texto>` | sessão de trabalho | arma a missão (só se o hook não armou) e começa |
| `context-guard`, `batch-eviction`, `handoff-load` | hooks de sempre | com missão armada: pedem handoff + clear em vez de "/clear", e repõem o texto da missão em toda geração |

A fonte dos dois comandos está em `zelador/commands/`; instalar é copiar para `~/.claude/commands/`.
Quem copia é o usuário: em 09/11 o classificador do modo auto negou a sessão escrevendo o próprio
`missao.md` lá ("Self-Modification").

## Uso

1. **Gate e armar registrados**: `python hooks/install.py --only clear-gate,mission-arm`. Ficam fora da
   instalação padrão: o gate é o único hook que responde permissão e o `mission-arm` grava o estado da missão.
   Só valem para CLI nova: sessão já aberta enxerga depois do próximo clear. Sem o `mission-arm` o `/missao`
   continua armando pelo modelo (Write + `--arquivo`).
2. **Zeladora**: sessão nova, modelo barato, mesmo modo de permissão das sessões de trabalho. `/zelador`.
   Uma por máquina.
3. **Trabalho**: `/missao <o que fazer, nas suas palavras>`.

Sem missão armada nenhum hook muda de comportamento. Sessão de terminal (sem
`CLAUDE_CODE_HOST_SESSION_ID`) nunca entra no ciclo.

## O ciclo para de propósito

- pergunta ao usuário que muda o desenho do projeto, ou passo irreversível sem aprovação: a sessão pergunta e fica;
- missão terminada: `missao.py concluir`, relato, sem clear;
- teto de clears (`--max-ciclos`, padrão 10) ou contexto abaixo do mínimo (`--min-ctx`, padrão 150k): o gate nega;
- sem vigia vivo, ou com a CLI da zeladora morta: o gate nega e a sessão avisa o usuário.

Desarmar à mão: `python zelador/missao.py concluir --host local_...`.
Desligar: arquivar a sessão zeladora ou matar o vigia (`vivo.json` tem o pid). Quando a CLI da zeladora
sai, o vigia termina com 6 e apaga o `vivo.json` (teste 7).

## Vigia

`python -I zelador/vigia.py [--espera 1800] [--max 10800] [--folga 5] [--cli PID] [--estado DIR]`

| saída | quer dizer | a zeladora |
|---|---|---|
| 0 | última linha `<hora> fim {"acao": "segue", "host": "local_...", ...}` | sobe o vigia de novo, depois manda `segue` ao host |
| 3 | `--max` passou sem pedido atendido (`max-estourou`) | sobe de novo |
| 6 | a CLI da zeladora morreu (`cli-morto`) | ninguém acorda; o gate passa a negar |
| 7 | já há vigia vivo | não sobe outro |

A ordem no código 0 importa: a sessão que recebe o `segue` pode pedir outro clear em segundos, e sem
vigia vivo o pedido dela é negado.

Estado em `~/.claude/zelador/`: `missoes/`, `pedidos/` (escritos pelo gate), `feitos/`, `rejeitados/`,
`vivo.json` (`pid`, `cli`, `host`, `desde`), `zelador.log` (uma linha JSON por evento).

Um pedido é rejeitado quando o JSON é inválido, o host não é `local_...`, o pid não é inteiro, ou o pid
não sai em `--espera`. O `segue` não sai quando a linhagem já tem geração nova depois do pedido (o usuário
digitou antes). `--espera` é longo de propósito: pedido rejeitado cedo demais é `segue` que nunca sai.

## Limites conhecidos

- **Um pedido por vez.** O vigia espera a CLI de um pedido (até `--espera`) antes de olhar o próximo, e
  sai a cada `segue`. Entre a saída e a volta dele (segundos) outra missão que peça clear é negada por
  falta de vigia. Com uma missão por vez não aparece.
- **`vivo.json` órfão.** Vigia morto sem limpar (reboot, kill da árvore) deixa pid e cli no arquivo; se o
  Windows reusar os dois números, o gate libera sem ninguém para mandar o `segue`. Exigir os dois vivos
  torna isso raro, não impossível. Conserto: batida periódica no arquivo.
- **Pid reusado.** Pedido lido depois de a CLI sair pode apontar para outro processo; o vigia espera
  `--espera` e rejeita.
- **Clear recusado depois do gate.** Se o app ou o classificador recusar o clear já liberado, o pedido
  fica até `--espera` e o contador de ciclos já andou.
- **Texto da missão copiado pelo modelo quando o hook não arma.** Com o `mission-arm` registrado o texto
  vai do teclado ao `missao.py` sem passar pelo modelo. Sem ele, ou se ele falhar (sem python, script
  recusou: sai calado), vale o caminho antigo do `/missao` (Write + `--arquivo`). O hook não lê opções:
  `--max-ciclos` e `--min-ctx` ficam no padrão; para mudar, `missao.py armar` no terminal.
- **`/missao` de novo troca a missão** e zera o contador de clears, com ou sem hook.
- **Remote Control.** A descrição da tool diz que sessão servindo cliente de Remote Control não pode ser
  limpa. Em 09/11 os 3 clears passaram com ele ligado na cobaia (`remoteControlActive: true`). Não isolado:
  cliente remoto com a sessão aberta na hora do clear.
- **Geração 2+ roda em turno de outra sessão.** O `segue` chega como mensagem de par (`origin.kind: "peer"`)
  e é nesse turno que a geração trabalha. Nas duas rodadas o modo auto aceitou tudo o que a missão pediu nesse
  tipo de turno: Bash e Write simples, o `missao.py concluir` e, na segunda, `git add`, `git commit`,
  `curl -sI` e o `rm` de um arquivo que a missão tinha criado. É n = 1 de cada, dentro da pasta do projeto e
  num repositório de rascunho: `git push`, escrita em rede e apagar fora da pasta seguem sem medição.
- **Zeladora cara para o que faz.** O contexto parado dela é de 104–110k tokens (Sonnet 5.5, nesta pasta) e
  cada `segue` são 3–4 chamadas lendo isso do cache. Parada mais de 1 h ela perde o cache (TTL de 1 h): no
  `segue` de 09/11 22:29, depois de 1 h 23 min, a 1ª chamada reescreveu 53k tokens e só leu os 58k do prefixo
  comum às sessões, que a cobaia (mesmo modelo) tinha escrito 39 s antes; sozinha, reescreveria os 111k. O
  vigia a acorda a cada `--max` (3 h) mesmo sem pedido, e essa acordada deve pagar a mesma reescrita (não
  medido).

## Medido

| data | o quê | resultado |
|---|---|---|
| 08/11 | fim de background acorda sessão ociosa | 2/2, turno em 0,1 s |
| 08/11 | `segue` enviado em turno aberto por evento | aceito; CLI nova em ~2 s |
| 08/11 | `clear_session("self")` em turno aberto por outra sessão, sem hook | 1 aceito, 1 negado pelo classificador |
| 09/11 | zeladora subida por brief (corpo do `zelador.md`, Sonnet 5.5, modo auto) | vigia no ar: `vivo.json` em 4 s |
| 09/11 | `missao.py armar` pedido por outra sessão (brief do `start_session`, modo auto, sem o `/missao`) | negado pelo classificador, `Reason: [Self-Modification]`; a missão não armou |
| 09/11 | ciclo inteiro com o gate: 1 cobaia Sonnet 5.5 em modo auto, missão armada pelo usuário no terminal, 3 clears, `--min-ctx 0` | 4 gerações, 3 handoffs encadeados, `FIM` em 2 min 36 s; 3× `pedido`/`pid-saiu`/`segue` no log, 1 `segue` por geração, `pedidos/` e `rejeitados/` vazios; a missão voltou pelo hook nas gerações 2 a 4 |
| 09/11 | `clear_session("self")` em turno aberto por outra sessão, com o `allow` do gate | 3/3 aceitos; decisão gravada como `"source":"hook"` (os Bash da mesma geração saem como `"reasonType":"classifier"`) |
| 09/11 | o mesmo com Remote Control ligado na cobaia | 3/3; nenhuma recusa "serving a Remote Control client" |
| 09/11 | do `clear_session` até o `segue` chegar na geração nova | 30,4 s, 23,0 s e 27,5 s: resto do turno 8,6–12,7 s, CLI sai em 1,6–2,2 s, folga do vigia 5,0 s, zeladora 4,6–7,2 s, CLI nova 3,1–4,3 s |
| 09/11 | ordem na zeladora | vigia de volta antes do `segue` nas 3 vezes (o `inicio` dele sai 1,5–4,4 s antes de a cobaia receber) |
| 09/11 | custo de uma geração da cobaia (Sonnet 5.5, missão de 3 comandos; `cost-state`) | US$ 0,27 (com o turno do `armar` negado), 0,25 e 0,16; 27–49k tokens de cache escritos por geração |
| 09/11 | `missao.py concluir` em turno aberto por outra sessão | aceito pelo classificador (o `armar` tinha sido negado) |
| 09/11 | hooks num `/comando` digitado: CLI 2.1.317 do app, headless, prompt por argv e por stream-json, hook que só grava a entrada | `UserPromptSubmit` e depois `UserPromptExpansion`, mesmo `prompt_id`; `prompt` cru nos dois; a expansão traz `command_name`, `command_args` (quebra de linha, linha vazia, aspas, `$VAR` e acento intactos) e `command_source`; bloquear em qualquer um custa 0 chamada |
| 09/11 | o `additionalContext` dos dois num turno de `/comando` (lido do transcript) | anexado depois do comando expandido, como `<system-reminder>` com o nome do evento |
| 09/11 | `mission-arm` registrado pelo `install.py --only` em config isolada, `/missao` de 2 linhas por stream-json na mesma CLI | missão gravada com o texto literal (espaço das pontas cortado), `projeto` = pasta da sessão; a linha "o hook ja armou" anexada ao turno. Modelo não chamado (config sem login): falta ver o modelo pular o passo de armar |
| 09/11 | os 2 comandos de instalação contra cópia do `settings.json` real | 1 entrada nova (`UserPromptExpansion`, matcher `missao`), o resto igual, sem `.bak` novo |
| 09/11 | um `/missao` vindo de outra sessão arma pelo `mission-arm`? | pela doc, não: em cross-session-messaging, "a command in the message's text, such as `/compact`, arrives as plain text", e o `UserPromptExpansion` é só de comando digitado (Skill chamado pelo modelo passa por `PreToolUse`). No transcript da cobaia o `segue` chega embrulhado em `<cross-session-message>`, nunca começando por `/`. Não medido com um `/missao` de par |
| 09/11 | `python` chamado pelo `node` como o hook chama (`spawnSync`, Bash da sessão, 4 vezes) | 239–280 ms, contra 4 s de limite; resolve para o Python 3.13 do WindowsApps. No ambiente de hook do app, não medido |
| 09/11 | `/missao` digitado numa sessão do app com o `mission-arm` instalado: CLI 2.1.317 subida para esse prompt, 15 s depois da gravação do `settings.json` com o hook; Fable 5, modo auto; lido do transcript (8a8f7abc) e do arquivo da missão | anexo `hook_additional_context` de `UserPromptExpansion` com a linha "o hook ja armou"; missão criada 0,5 s depois de o prompt entrar na fila e 0,4 s antes da 1ª chamada à API; `texto` igual ao `command-args` byte a byte (153 bytes, mesmo sha256); o modelo não fez Write nem `missao.py armar`, só `status` e `concluir`; `python` resolveu no ambiente de hook do app. n = 1, texto de uma linha |
| 09/11 | rodada com trabalho real na geração aberta pelo `segue`: mesma cobaia (Sonnet 5.5, modo auto, Remote Control ligado), missão armada pelo usuário no terminal (`--max-ciclos 1`, `--min-ctx 0`), 1ª geração iniciada por mensagem de outra sessão | 2 gerações, 1 handoff, `FIM` em 1 min 44 s; 1× `pedido`/`pid-saiu`/`segue` no log, `pedidos/` e `rejeitados/` vazios; clear aceito com `"source":"hook"`; a missão voltou pelo hook na geração 2; 17 chamadas de ferramenta nas duas gerações, nenhuma negada nem com erro |
| 09/11 | trabalho real em turno aberto pelo `segue` (`origin.kind: "peer"`), modo auto: `git add`, `git commit`, `curl -sI https://example.com` e `rm` de um arquivo que a missão criou na geração 1 | 4/4 aceitos e sem erro: commit `871b432` no repositório de rascunho, HTTP 200, arquivo apagado (conferido por fora com `git log` e `ls`). Decisão gravada com `"reasonType":"classifier"` em add, commit e curl e `"reasonType":"mode"` no `rm`. n = 1 de cada, tudo dentro da pasta do projeto. O modelo acrescentou por conta própria um `Co-Authored-By` à mensagem do commit |
| 09/11 | do `clear_session` até o `segue` chegar, com a zeladora parada havia 1 h 23 min | 32,0 s: resto do turno 8,1 s, CLI sai em 1,6 s, folga do vigia 5,1 s, zeladora 12,7 s (eram 4,6–7,2 s), CLI nova 4,5 s. Marcos: `tool_use` do clear, `stop_hook_summary`, `pid-saiu`, `segue` do vigia, `SendMessage` da zeladora, mensagem na cobaia |
| 09/11 | cache depois de mais de 1 h parada (`usage` da 1ª chamada de cada turno, lido dos transcripts) | cobaia, 1 h 22 min parada: leu 0 e escreveu 105.434 tokens. Zeladora, 1 h 23 min parada, 39 s depois: escreveu 53.277 e leu 58.158. A geração 2 da cobaia, conversa nova, leu os mesmos 58.158. Leitura, não isolada: os 58.158 são o prefixo comum às sessões do mesmo modelo, que a cobaia tinha acabado de escrever. Cache escrito por geração da cobaia: 109k (fria) e 49k. n = 1 |

A 1ª tentativa do ciclo (09/11, 23:55Z) parou no `armar`, antes do primeiro clear; a que está na tabela é a
2ª (10/11 00:04Z a 00:06Z, 21:04 em Brasília). O que ela não diz: missão de 3 comandos, contexto pequeno,
um modelo, n = 3. A rodada com trabalho real foi em 10/11, 01:29Z a 01:31Z (22:29 em Brasília): 1 clear, 4
comandos reais num repositório de rascunho, um modelo, n = 1 de cada. O clear pedido pela guarda de contexto
segue sem medição. Do `/missao` armando por hook há a medição headless e sem login (n = 1 por caso) e uma
sessão do app com modelo (n = 1, texto de uma linha).
