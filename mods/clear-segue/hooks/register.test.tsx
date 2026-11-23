import { expect, mock, test } from 'claude-code/testing'

const BAND = {
  plugin: 'clear-segue',
  surface: 'desktop',
  component: 'AbovePrompt',
  props: {
    hasSurvey: false,
    isCollapsed: false,
    isWorking: false,
    maxRows: 3,
    bodyColumns: 80,
    scroll: { offset: 0, bodyRows: 3 },
    view: {},
  },
} as const

const CWD = '/proj'
const REL = '.claude/handoff-abcdef12.md'
const T0 = 1_000_000

// O mundo embaixo do mod. `mtime` undefined = handoff nao existe.
function mundo(
  on: any,
  o: { mtime?: number; armed?: unknown; clearFalha?: boolean; cwd?: string },
) {
  const w = {
    mtime: o.mtime,
    cmds: [] as string[],
    prompts: [] as string[],
    toasts: [] as string[],
    store: new Map<string, unknown>(),
    clock: mock.clock(on, { now: T0 }),
  }

  if (o.armed !== undefined) w.store.set('armed', o.armed)
  on('store.get', (_: unknown, e: any) => ({ value: w.store.get(e.key) }))
  on('store.set', (_: unknown, e: any) => {
    w.store.set(e.key, e.value)

    return { value: undefined }
  })
  on('store.delete', (_: unknown, e: any) => {
    w.store.delete(e.key)

    return { value: undefined }
  })
  on('session.root', () => ({ value: CWD }))
  on('session.cwd', () => ({ value: o.cwd ?? CWD }))
  on('session.id', () => ({ value: 'abcdef12-0000-0000-0000-000000000000' }))
  on('fs.stat', (_: unknown, e: any) => {
    // No Windows o motor entrega o caminho normalizado (C:\proj\...).
    expect(e.path.replace(/\\/g, '/').replace(/^[A-Z]:/, '')).toBe(
      `${CWD}/${REL}`,
    )
    if (w.mtime === undefined) throw new Error('ENOENT')

    return { value: { kind: 'file', size: 10, mtimeMs: w.mtime, isLink: false } }
  })
  on('command.run', (_: unknown, e: any) => {
    if (o.clearFalha) throw new Error('nao rodou')
    w.cmds.push(e.command)

    return { text: '' }
  })
  on('prompt.submit', (_: unknown, e: any) => {
    w.prompts.push(e.text)

    return { text: e.text }
  })
  on('ui.toast', (_: unknown, e: any) => {
    w.toasts.push(typeof e === 'string' ? e : (e.text ?? JSON.stringify(e)))

    return { value: undefined }
  })
  on('tool.call', () => ({ result: {} }))
  on('turn.complete', () => ({ text: '' }))

  return w
}

const fim = (reason: 'answer' | 'aborted' = 'answer') =>
  ({
    reason,
    answer: '',
    durationMs: 1,
    isAborted: reason === 'aborted',
    turnId: 't1',
  }) as const

async function chaves(ui: any): Promise<string[]> {
  const ks: string[] = []

  for (const k of ['segue', 'cancelar', 'denovo', 'forcar', 'clear-segue', 'clear'])
    if ((await ui.find({ key: k })) !== undefined) ks.push(k)

  return ks
}

test('handoff em dia: Clear + Segue limpa e manda o segue', async ($, on) => {
  const w = mundo(on, { mtime: T0 })
  // Leitura e ferramenta do app depois do handoff nao o deixam defasado.
  await w.clock.advance(60_000)
  await $.tool.call({ tool: 'Read', file_path: '/x' } as any)
  await $.tool.call({ tool: 'mcp__ccd_turn__wrap_up', recap: 'x' } as any)

  const ui = await $.ui.mount(BAND)
  expect(await chaves(ui)).toEqual(['clear-segue', 'clear'])
  await ui.press({ key: 'clear-segue' })

  expect(w.cmds).toEqual(['clear'])
  expect(w.prompts.length).toBe(1)
  expect(w.prompts[0]).toContain(`segue pelo handoff ${REL}`)
  expect(w.store.has('armed')).toBe(false)
  await ui.unmount()
})

test('So clear: limpa, arma, e o botao Segue manda o segue', async ($, on) => {
  const w = mundo(on, { mtime: T0 })

  const ui = await $.ui.mount(BAND)
  await ui.press({ key: 'clear' })
  expect(w.cmds).toEqual(['clear'])
  expect(w.prompts).toEqual([])
  expect((w.store.get('armed') as any)?.handoff).toBe(REL)
  await ui.unmount()

  const ui2 = await $.ui.mount(BAND)
  expect(await chaves(ui2)).toEqual(['segue'])
  await ui2.press({ key: 'segue' })
  expect(w.prompts.length).toBe(1)
  expect(w.prompts[0]).toContain(`segue pelo handoff ${REL}`)
  expect(w.store.has('armed')).toBe(false)
  await ui2.unmount()

  const ui3 = await $.ui.mount(BAND)
  expect(await chaves(ui3)).toEqual(['clear-segue', 'clear'])
  await ui3.unmount()
})

test('armado vencido (30 min) ou de outra pasta nao mostra Segue', async ($, on) => {
  const w = mundo(on, {
    mtime: T0,
    armed: { cwd: CWD, at: T0 - 31 * 60 * 1000, handoff: REL },
  })

  const ui = await $.ui.mount(BAND)
  expect(await chaves(ui)).toEqual(['clear-segue', 'clear'])
  await ui.unmount()

  w.store.set('armed', { cwd: '/outra', at: T0, handoff: REL })
  const ui2 = await $.ui.mount(BAND)
  expect(await chaves(ui2)).toEqual(['clear-segue', 'clear'])
  await ui2.unmount()
})

test('defasado: pede atualizacao e o clear sai no fim do turno', async ($, on) => {
  const w = mundo(on, { mtime: T0 })
  await w.clock.advance(60_000)
  await $.tool.call({ tool: 'Bash', command: 'ls' } as any)

  const ui = await $.ui.mount(BAND)
  await ui.press({ key: 'clear-segue' })
  expect(w.cmds).toEqual([])
  expect(w.prompts.length).toBe(1)
  expect(w.prompts[0]).toContain(`atualize o handoff desta sessao em ${CWD}/${REL}`)
  await ui.unmount()

  const ui2 = await $.ui.mount(BAND)
  expect(await chaves(ui2)).toEqual(['cancelar'])
  await ui2.unmount()

  // O modelo regrava o handoff (Write conta como obra, a folga de 5 s cobre).
  await w.clock.advance(10_000)
  await $.tool.call({ tool: 'Write', file_path: '/x', content: '' } as any)
  w.mtime = w.clock.now()
  await $.turn.complete(fim())
  expect(w.cmds).toEqual([])
  await w.clock.advance(300)

  expect(w.cmds).toEqual(['clear'])
  expect(w.prompts.length).toBe(2)
  expect(w.prompts[1]).toContain(`segue pelo handoff ${REL}`)
  expect(w.store.has('armed')).toBe(false)
})

test('sem handoff + So clear: pede gravacao, limpa no fim do turno, sem segue', async ($, on) => {
  const w = mundo(on, {})

  const ui = await $.ui.mount(BAND)
  await ui.press({ key: 'clear' })
  expect(w.prompts[0]).toContain(`escreva o handoff desta sessao em ${CWD}/${REL}`)
  await ui.unmount()

  w.mtime = w.clock.now()
  await $.turn.complete(fim())
  await w.clock.advance(300)

  expect(w.cmds).toEqual(['clear'])
  expect(w.prompts.length).toBe(1)
  expect((w.store.get('armed') as any)?.handoff).toBe(REL)
})

test('cancelar: o fim do turno nao limpa', async ($, on) => {
  const w = mundo(on, {})

  const ui = await $.ui.mount(BAND)
  await ui.press({ key: 'clear-segue' })
  await ui.unmount()

  const ui2 = await $.ui.mount(BAND)
  await ui2.press({ key: 'cancelar' })
  await ui2.unmount()

  w.mtime = w.clock.now()
  await $.turn.complete(fim())
  await w.clock.advance(1000)
  expect(w.cmds).toEqual([])

  const ui3 = await $.ui.mount(BAND)
  expect(await chaves(ui3)).toEqual(['clear-segue', 'clear'])
  await ui3.unmount()
})

test('turno interrompido: clear automatico cancelado', async ($, on) => {
  const w = mundo(on, {})

  const ui = await $.ui.mount(BAND)
  await ui.press({ key: 'clear-segue' })
  await ui.unmount()

  w.mtime = w.clock.now()
  await $.turn.complete(fim('aborted'))
  await w.clock.advance(1000)
  expect(w.cmds).toEqual([])

  const ui2 = await $.ui.mount(BAND)
  expect(await chaves(ui2)).toEqual(['clear-segue', 'clear'])
  await ui2.unmount()
})

test('handoff nao gravado no turno: clear cancelado, botoes normais', async ($, on) => {
  const w = mundo(on, {})

  const ui = await $.ui.mount(BAND)
  await ui.press({ key: 'clear-segue' })
  await ui.unmount()

  await $.turn.complete(fim())
  await w.clock.advance(1000)
  expect(w.cmds).toEqual([])

  const ui2 = await $.ui.mount(BAND)
  expect(await chaves(ui2)).toEqual(['clear-segue', 'clear'])
  await ui2.unmount()
})

test('continua defasado: botoes de falha; "Clear assim mesmo" limpa e segue', async ($, on) => {
  const w = mundo(on, { mtime: T0 })
  await w.clock.advance(60_000)
  await $.tool.call({ tool: 'Bash', command: 'ls' } as any)

  const ui = await $.ui.mount(BAND)
  await ui.press({ key: 'clear-segue' })
  await ui.unmount()

  // O turno termina sem regravar o handoff.
  await $.turn.complete(fim())
  await w.clock.advance(1000)
  expect(w.cmds).toEqual([])

  const ui2 = await $.ui.mount(BAND)
  expect(await chaves(ui2)).toEqual(['denovo', 'forcar'])
  await ui2.press({ key: 'forcar' })
  expect(w.cmds).toEqual(['clear'])
  expect(w.prompts.length).toBe(2)
  expect(w.prompts[1]).toContain(`segue pelo handoff ${REL}`)
  await ui2.unmount()
})

test('continua defasado: "Atualizar de novo" pede outra vez e limpa no fim', async ($, on) => {
  const w = mundo(on, { mtime: T0 })
  await w.clock.advance(60_000)
  await $.tool.call({ tool: 'Bash', command: 'ls' } as any)

  const ui = await $.ui.mount(BAND)
  await ui.press({ key: 'clear-segue' })
  await ui.unmount()
  await $.turn.complete(fim())
  await w.clock.advance(1000)

  const ui2 = await $.ui.mount(BAND)
  await ui2.press({ key: 'denovo' })
  expect(w.prompts.length).toBe(2)
  expect(w.prompts[1]).toContain('atualize o handoff')
  await ui2.unmount()

  w.mtime = w.clock.now()
  await $.turn.complete(fim())
  await w.clock.advance(300)
  expect(w.cmds).toEqual(['clear'])
  expect(w.prompts.length).toBe(3)
  expect(w.prompts[2]).toContain('segue pelo handoff')
})

test('o /clear falha: desarma e nao manda segue', async ($, on) => {
  const w = mundo(on, { mtime: T0, clearFalha: true })

  const ui = await $.ui.mount(BAND)
  await ui.press({ key: 'clear-segue' })
  expect(w.prompts).toEqual([])
  expect(w.store.has('armed')).toBe(false)
  await ui.unmount()

  const ui2 = await $.ui.mount(BAND)
  expect(await chaves(ui2)).toEqual(['clear-segue', 'clear'])
  await ui2.unmount()
})

test('prompt digitado com o Segue armado desarma', async ($, on) => {
  const w = mundo(on, { mtime: T0, armed: { cwd: CWD, at: T0, handoff: REL } })

  await $.prompt.submit({ text: 'outra coisa' } as any)
  expect(w.store.has('armed')).toBe(false)
})

// Medido em 23/11 (sessao PRO-EX): o shell fez cd para <projeto>/.claude e o
// mod, lendo o cwd, nunca achava o handoff.
test('cwd movido por cd: o handoff e o armado seguem a raiz do projeto', async ($, on) => {
  const w = mundo(on, { mtime: T0, cwd: `${CWD}/.claude` })

  const ui = await $.ui.mount(BAND)
  await ui.press({ key: 'clear' })
  expect(w.cmds).toEqual(['clear'])
  expect(w.prompts).toEqual([])
  expect((w.store.get('armed') as any)?.cwd).toBe(CWD)
  await ui.unmount()

  const ui2 = await $.ui.mount(BAND)
  expect(await chaves(ui2)).toEqual(['segue'])
  await ui2.unmount()
})
