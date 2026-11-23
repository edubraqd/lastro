import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Armed } from '../types'

const isArmed = atom({ plugin: 'clear-segue', key: 'isArmed' } as const, false)
const isStale = atom({ plugin: 'clear-segue', key: 'isStale' } as const, false)
const isUpdating = atom(
  { plugin: 'clear-segue', key: 'isUpdating' } as const,
  false,
)

// O /clear pode derrubar o processo: o "armado" mora no $.store, por pasta.
// A pasta e lida na hora (pasta, abaixo): no app a sessao nasce de um processo
// reserva, e o cwd do session.start e o da reserva, nao o do projeto.
const KEY = 'armed'
const VALIDADE_MS = 30 * 60 * 1000
// Folga entre a escrita do handoff e o fim da propria chamada que o escreveu.
const FOLGA_MS = 5000
// Chamadas que nao mudam a arvore nem o que o handoff deveria contar: leitura
// e as ferramentas do proprio app (lista de tarefas, wrap_up). Sem isto, o
// wrap_up depois de gravar o handoff ja o deixava "defasado".
const NAO_E_OBRA =
  /^(Read|Grep|Glob|ToolSearch|Skill|ReadNotifications|AskUserQuestion)$|^mcp__ccd_/

// Memoria do processo (some num reload; o $.store cobre o que precisa durar).
const mem: {
  ultimaObra: number
  obras: number[]
  // Clear pedido com o handoff faltando ou defasado: o modelo esta gravando,
  // e o fim desse turno dispara o clear sozinho.
  pendente: { seguir: boolean } | undefined
} = { ultimaObra: 0, obras: [], pendente: undefined }

// A pasta do projeto, nao o cwd: um `cd` do shell move o cwd (medido 23/11,
// sessao em <projeto>/.claude procurava .claude/.claude/handoff-*.md, nunca
// achava e cancelava o clear) e nao move a raiz.
async function pasta($: EngineInterface): Promise<string> {
  return $.session.root().catch(() => $.session.cwd())
}

async function lerArmado($: EngineInterface): Promise<Armed | undefined> {
  const a = (await $.store.get(KEY)) as Armed | undefined
  const vale =
    a !== undefined &&
    a.cwd === (await pasta($)) &&
    (await $.clock.now()) - a.at < VALIDADE_MS

  return vale ? a : undefined
}

async function relHandoff($: EngineInterface): Promise<string> {
  return `.claude/handoff-${(await $.session.id()).slice(0, 8)}.md`
}

// O handoff desta sessao: <pasta>/.claude/handoff-<8 primeiros do id>.md,
// como o context-guard do Lastro escreve. O nome leva o id da sessao, que muda
// a cada /clear: existir ja prova que e desta geracao. Devolve o caminho
// relativo e quantas chamadas de obra houve depois da ultima escrita, ou
// undefined se nao existe.
async function handoff(
  $: EngineInterface,
): Promise<{ rel: string; depois: number } | undefined> {
  const rel = await relHandoff($)
  const raiz = await pasta($)
  const cwd = await $.session.cwd()
  // Raiz primeiro; o cwd so como rede, caso a raiz nao seja a do projeto.
  const st =
    (await $.fs.stat(`${raiz}/${rel}`).catch(() => undefined)) ??
    (cwd === raiz
      ? undefined
      : await $.fs.stat(`${cwd}/${rel}`).catch(() => undefined))

  if (st === undefined || st.kind !== 'file') return undefined

  const corte = st.mtimeMs + FOLGA_MS

  return {
    rel,
    depois: mem.ultimaObra > corte ? mem.obras.filter(t => t > corte).length : 0,
  }
}

// O SessionStart do Lastro ja injeta o handoff na sessao nova: mandar reler o
// arquivo custaria uma chamada e os mesmos tokens de novo. Verificar, nao
// confiar: o sucessor que acredita na leitura do antecessor erra mais
// (Handoff Debt, "Choosing a Handoff View").
function textoSegue(rel: string | undefined): string {
  return rel === undefined
    ? 'segue'
    : `segue pelo handoff ${rel}. Se ele ja esta no contexto (injetado no inicio da sessao), nao releia; senao leia so ele. Confira o que ele afirma contra a arvore e retome da proxima acao segura`
}

async function desarmar($: EngineInterface): Promise<void> {
  await $.store.delete(KEY)
  await update($, isArmed, () => false)
}

// Um clique: arma, limpa e, com seguir, manda o segue sozinho. Se o /clear
// derrubar o processo o await nao volta, mas o armado esta no $.store e o
// botao Segue aparece na volta.
async function limpar(
  $: EngineInterface,
  rel: string,
  seguir: boolean,
): Promise<void> {
  const a: Armed = {
    cwd: await pasta($),
    at: await $.clock.now(),
    handoff: rel,
  }
  await $.store.set(KEY, a)
  await update($, isStale, () => false)
  await update($, isUpdating, () => false)
  await update($, isArmed, () => true)

  const ok = await $.command.run({ command: 'clear' }).then(
    () => true,
    () => false,
  )

  if (!ok) {
    await desarmar($)
    $.ui.toast('O /clear nao rodou: nada foi limpo')

    return
  }

  mem.ultimaObra = 0
  mem.obras = []

  if (!seguir) return

  await desarmar($)
  void $.prompt.submit({ text: textoSegue(rel), asUser: true })
}

// O clique no Clear. Handoff em dia: limpa ja. Faltando ou defasado: pede ao
// modelo que grave e deixa o clear pendurado no fim desse turno, sem 2o clique.
async function pedirClear($: EngineInterface, seguir: boolean): Promise<void> {
  const h = await handoff($)

  if (h !== undefined && h.depois === 0) {
    await limpar($, h.rel, seguir)

    return
  }

  const rel = await relHandoff($)
  // Caminho inteiro no pedido: relativo, um modelo com o shell em outra pasta
  // gravaria fora de onde o mod procura.
  const abs = `${await pasta($)}/${rel}`
  mem.pendente = { seguir }
  await update($, isStale, () => false)
  await update($, isUpdating, () => true)
  $.ui.toast(
    h === undefined
      ? `Sem ${rel}: gravando antes do clear`
      : `Handoff defasado (${h.depois} chamada(s) depois dele): atualizando antes do clear`,
  )
  void $.prompt.submit({
    text: `${h === undefined ? 'escreva' : 'atualize'} o handoff desta sessao em ${abs} com o estado atual (feito com prova, pendente em ordem, o que foi tentado e descartado, proxima acao segura) e pare: nenhuma outra ferramenta depois de gravar, sem wrap_up. O clear vem sozinho em seguida`,
    asUser: true,
  })
}

export const register: Register = on => {
  // Fim da ultima chamada de obra e quantas houve: handoff mais velho que
  // isso nao viu o trabalho feito depois dele (Handoff Debt: a nota que
  // omite evidencia custa redescoberta ao sucessor).
  on('tool.call', async ($, e, next) => {
    const r = await next(e)

    if (!NAO_E_OBRA.test(e.tool)) {
      mem.ultimaObra = await $.clock.now()
      mem.obras = [...mem.obras.slice(-199), mem.ultimaObra]
    }

    return r
  })

  // Qualquer prompt (o "segue" do botao ou um digitado) desarma.
  on('prompt.submit', async ($, e, next) => {
    const armado =
      (await read($, isArmed)) || (await lerArmado($)) !== undefined

    if (!e.command && armado) await desarmar($)

    return next(e)
  })

  // Fim do turno que gravou o handoff: se ficou em dia, o clear sai daqui.
  on('turn.complete', async ($, e, next) => {
    const p = mem.pendente

    if (p === undefined || e.agentId !== undefined) return next(e)

    mem.pendente = undefined
    await update($, isUpdating, () => false)

    if (e.reason !== 'answer') {
      $.ui.toast('Turno interrompido: clear automatico cancelado')

      return next(e)
    }

    const h = await handoff($)

    if (h === undefined || h.depois > 0) {
      $.ui.toast(
        h === undefined
          ? 'O handoff nao foi gravado: clear cancelado'
          : `O handoff continua defasado (${h.depois} chamada(s) depois dele)`,
      )
      await update($, isStale, () => h !== undefined)

      return next(e)
    }

    // Fora do hook: o turno espera por ele, e o /clear so roda com a sessao
    // ociosa.
    $.clock.after(300, () => {
      void limpar($, h.rel, p.seguir)
    })

    return next(e)
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (e.props.hasSurvey) return next(e)

    const { Box, Button } = $.ui.resolve(e)
    const a = await lerArmado($)
    const segue = (await read($, isArmed)) || a !== undefined

    // So aparece se o segue automatico nao saiu (o /clear reiniciou o
    // processo) ou depois do "So clear".
    if (segue) {
      return (
        <Box>
          <Button
            key="segue"
            label="Segue"
            variant="primary"
            onPress={async () => {
              const b = await lerArmado($)
              await desarmar($)
              void $.prompt.submit({ text: textoSegue(b?.handoff), asUser: true })
            }}
          />
        </Box>
      )
    }

    if (await read($, isUpdating)) {
      return (
        <Box>
          <Button
            key="cancelar"
            label="Gravando handoff… cancelar o clear"
            onPress={async () => {
              mem.pendente = undefined
              await update($, isUpdating, () => false)
            }}
          />
        </Box>
      )
    }

    if (await read($, isStale)) {
      return (
        <Box>
          <Button
            key="denovo"
            label="Atualizar handoff de novo"
            variant="primary"
            onPress={() => pedirClear($, true)}
          />
          <Button
            key="forcar"
            label="Clear assim mesmo"
            onPress={async () => {
              const h = await handoff($)
              if (h !== undefined) await limpar($, h.rel, true)
            }}
          />
        </Box>
      )
    }

    return (
      <Box>
        <Button
          key="clear-segue"
          label="Clear + Segue"
          variant="primary"
          onPress={() => pedirClear($, true)}
        />
        <Button key="clear" label="Só clear" onPress={() => pedirClear($, false)} />
      </Box>
    )
  })
}
