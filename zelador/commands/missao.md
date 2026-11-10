---
description: Arma uma missão nesta sessão — ela segue sozinha (handoff, clear, "segue" do zelador) até terminar ou precisar de você
argument-hint: <a missão, nas suas palavras>
allowed-tools: Bash(python D:/claude-context-forensics/zelador/missao.py:*), Write
---

A missão desta sessão, nas palavras do usuário:

<mission>
$ARGUMENTS
</mission>

Se não veio texto entre as tags: rode `python D:/claude-context-forensics/zelador/missao.py status`,
mostre o estado em uma linha e pare.

**1. Arme, se o hook ainda não armou.** Se o contexto deste turno traz a linha do hook
`ZELADOR: o hook ja armou esta missao` (em inglês, `the hook has already armed this mission`), o texto já
está gravado na íntegra: não grave nada, não rode `armar`, faça o que a linha pedir e vá para o passo 2.

Sem essa linha, arme você. Grave o texto entre as tags num arquivo `missao.txt` do seu scratchpad com
Write, sem mudar um caractere: ele volta na íntegra a cada geração, e resumo ou correção aqui vira missão
errada lá na frente. Depois:

```bash
python D:/claude-context-forensics/zelador/missao.py armar --arquivo "<caminho do missao.txt>"
```

Leia o JSON que ele imprime. Com `vigia_vivo: false`, avise em uma linha que sem zeladora o clear
automático é negado e que ela sobe com `/zelador` em outra sessão. Não espere por isso: comece.

**2. Trabalhe na missão**, do jeito normal. O que muda com ela armada:

- Quando a guarda de contexto avisar (o aviso traz a instrução): escreva o handoff em
  `.claude/handoff-<8 primeiros caracteres de $CLAUDE_CODE_SESSION_ID>.md` na pasta do projeto, chame
  `clear_session` com `session_id: "self"` e encerre o turno sem mais nada. A ferramenta é adiada:
  ToolSearch `select:mcp__ccd_session_mgmt__clear_session` antes. A zeladora manda o "segue" e a geração
  seguinte recomeça do handoff, com este texto de missão de novo na frente.
- Não limpe antes desse aviso: abaixo do contexto mínimo o clear é negado.
- Clear negado: o motivo vem na resposta do hook. Faça o que ele diz; não tente outro caminho para limpar.
- **Pare e pergunte, sem limpar**, quando a resposta do usuário mudar o desenho do projeto ou quando o
  próximo passo for irreversível e ainda não aprovado.
- **Missão terminada**: `python D:/claude-context-forensics/zelador/missao.py concluir`, relate o que foi
  feito e não limpe.
