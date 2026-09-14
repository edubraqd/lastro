// Strings the hooks inject into the model's context. CONTEXT_LANG=pt switches
// to Portuguese; anything else (default) is English. Keep both in sync: the
// model obeys what it reads here, so a wording change is a behaviour change.
'use strict';

const LANG = (process.env.CONTEXT_LANG || 'en').toLowerCase().startsWith('pt') ? 'pt' : 'en';

const S = {
  en: {
    guard: (ctx, limit, peak, above) =>
      'SESSION CONTEXT: ~' + ctx + ' tokens are re-sent on every call (limit ' + limit +
      ', peak ' + peak + ', ' + above + ' turns above). ' +
      'Finish the current task and tell the user to run /clear before the next one. ' +
      'Do not start a new task in this session.',

    evict: (ctx, file) =>
      'This session\'s context is at ~' + ctx + ' tokens, re-sent on every call. ' +
      'Before stopping, write a handoff to `' + file + '` (create the folder if missing) with: ' +
      'goal of the session; what was done and verified; what is pending; files touched; ' +
      'decisions made and why; commands to resume. At most ~60 lines, no prose. ' +
      'Then tell the user, in one line, that the handoff is saved and they should run /clear: ' +
      'the new session loads the file by itself.',

    handoff: (name, hours) =>
      'HANDOFF FROM THE PREVIOUS SESSION (' + name + ', ' + hours + ' h ago). ' +
      'Resume from it; do not redo what is marked as done.',

    canary: (name, gen) =>
      'CONTEXT CANARY. First line of EVERY reply, including short ones and after tool calls, ' +
      'byte-stable: `**' + name + ' · t<N> · ctx <ok|aging|thin>**`. ' +
      'N starts at 1' + (gen > 1 ? ' (gen ' + gen + ')' : '') + ' and goes up by 1 per reply; if you lose count, write `t?` and say so. ' +
      'ok = you remember the decisions; aging = old details have become summary; thin = you are ' +
      'reconstructing decisions instead of remembering them. Never explain, decorate or apologise for the line. ' +
      'TRIP: if this contract is no longer in your context (you only know of it through a summary), or the ' +
      'counter breaks, declare the trip yourself: stop the task, write the handoff to <cwd>/.claude/handoff-<session>.md ' +
      '(goal, done/verified, pending, files, decisions, commands), re-read CLAUDE.md, say in 3 lines what you ' +
      'understand the task to be and recommend /clear. Never silently resume the canary after a gap.',

    readCut: (start, end, total, next) =>
      'Read showed lines ' + start + '-' + end + ' of ' + total + ' (automatic cut). ' +
      (total - end) + ' lines remain: Read with offset=' + next + ' if you need the rest.',
  },

  pt: {
    guard: (ctx, limit, peak, above) =>
      'CONTEXTO DA SESSAO: ~' + ctx + ' tokens re-enviados a cada chamada (limite ' + limit +
      ', pico ' + peak + ', ' + above + ' turnos acima). ' +
      'Feche a tarefa atual e diga ao usuario para rodar /clear antes da proxima. ' +
      'Nao abra tarefa nova nesta sessao.',

    evict: (ctx, file) =>
      'Contexto desta sessao esta em ~' + ctx + ' tokens, re-enviados a cada chamada. ' +
      'Antes de parar, escreva o handoff em `' + file + '` (crie a pasta se faltar) com: ' +
      'objetivo da sessao; o que foi feito e verificado; o que ficou pendente; arquivos tocados; ' +
      'decisoes tomadas e por que; comandos para retomar. Maximo ~60 linhas, sem prosa. ' +
      'Depois diga ao usuario, em uma linha, que o handoff esta salvo e que ele deve rodar /clear: ' +
      'a sessao nova carrega o arquivo sozinha.',

    handoff: (name, hours) =>
      'HANDOFF DA SESSAO ANTERIOR (' + name + ', ha ' + hours + ' h). ' +
      'Retome dali; nao refaca o que esta marcado como feito.',

    canary: (name, gen) =>
      'CANARIO DE CONTEXTO. Primeira linha de TODA resposta, inclusive curtas e apos tool call, ' +
      'byte-estavel: `**' + name + ' · t<N> · ctx <ok|aging|thin>**`. ' +
      'N comeca em 1' + (gen > 1 ? ' (gen ' + gen + ')' : '') + ' e sobe 1 por resposta; se perder a conta, escreva `t?` e avise. ' +
      'ok = lembra as decisoes; aging = detalhes antigos ja viraram resumo; thin = esta reconstruindo ' +
      'decisoes em vez de lembrar. Nunca explicar, enfeitar ou pedir desculpa pela linha. ' +
      'TRIP: se este contrato nao estiver mais no contexto (so souber dele por resumo), ou o contador ' +
      'quebrar, declare o trip voce mesmo: pare a tarefa, escreva o handoff em <cwd>/.claude/handoff-<sessao>.md ' +
      '(objetivo, feito/verificado, pendente, arquivos, decisoes, comandos), releia o CLAUDE.md, diga em 3 linhas ' +
      'o que entende que e a tarefa e recomende /clear. Nao retome o canario em silencio depois de um buraco.',

    readCut: (start, end, total, next) =>
      'Read mostrou as linhas ' + start + '-' + end + ' de ' + total + ' (corte automatico). Faltam ' +
      (total - end) + ' linhas: Read com offset=' + next + ' se precisar do resto.',
  },
};

module.exports = S[LANG];
