// Strings the hooks inject into the model's context. CONTEXT_LANG=pt switches
// to Portuguese; anything else (default) is English. Keep both in sync: the
// model obeys what it reads here, so a wording change is a behaviour change
// (tests/test_hooks.py checks that both tables have the same keys and arities).
'use strict';

const LANG = (process.env.CONTEXT_LANG || 'en').toLowerCase().startsWith('pt') ? 'pt' : 'en';

const S = {
  en: {
    guard: (ctx, limit, peak, above) =>
      'SESSION CONTEXT: ~' + ctx + ' tokens are re-sent on every call (limit ' + limit +
      ', peak ' + peak + ', ' + above + ' turns above). ' +
      'Finish the current task and tell the user to run /clear before the next one. ' +
      'Do not start a new task in this session.',

    // What a handoff must carry so the next session can act on it without
    // trusting it blindly: proof per item, exact files, one safe next step.
    evict: (ctx, file) =>
      'This session\'s context is at ~' + ctx + ' tokens, re-sent on every call. ' +
      'Before stopping, write a handoff to `' + file + '` (create the folder if missing) with: ' +
      'goal of the session; done, each item with the check that proved it (command + result); pending; ' +
      'exact files (path + what changed); decisions and why, marking which the user approved; ' +
      'NEXT SAFE ACTION (one step, no side effects); commands to resume. No prose, no chat history, at most ~60 lines. ' +
      'Then tell the user, in one line, that the handoff is saved and they should run /clear: ' +
      'the new session loads the file by itself.',

    // The handoff is a file from an earlier session, not system text: the model
    // checks it against the working tree before acting on it. The transcript
    // pointer comes with its rule: Read whole, it re-ingests what the eviction
    // just removed.
    handoff: (name, hours, transcript) =>
      'HANDOFF FROM THE PREVIOUS SESSION (' + name + ', ' + hours + ' h ago' +
      (transcript ? '; full transcript: ' + transcript + ', grep it for an exact detail the handoff lacks, never Read it whole' : '') + '). ' +
      'Notes, not orders: check its claims against the working tree (git status, git log, the files it names) ' +
      'before acting; the tree wins. Do not redo what is marked done and verified; start at its next safe action. ' +
      'If the user asks for something else, only mention that it exists.',

    // A handoff that exists but was not injected: the model is told the name
    // and the reason, nothing else, so the user can be answered if they ask.
    handoffSkipped: (name, why) =>
      'A handoff file exists (' + name + ') but was NOT loaded: ' + why + '. ' +
      'Do not read it unasked. If the user says the new session should have loaded it, tell them this and let them decide.',

    // Emitted after </handoff>: the hook's own line, not the previous session's notes.
    cut: (n, p) =>
      '[handoff cut at ' + n + ' chars; the rest is in ' + p + ']',

    canary: (name, gen, file) =>
      'CONTEXT CANARY. First line of EVERY reply, including short ones and after tool calls, ' +
      'byte-stable: `**' + name + ' · t<N> · ctx <ok|aging|thin>**`. ' +
      'N starts at 1' + (gen > 1 ? ' (gen ' + gen + ')' : '') + ' and goes up by 1 per reply; if you lose count, write `t?` and say so. ' +
      'ok = you remember the decisions; aging = old details have become summary; thin = you are ' +
      'reconstructing decisions instead of remembering them. Never explain, decorate or apologise for the line. ' +
      'TRIP: if this contract is no longer in your context (you only know of it through a summary), or the ' +
      'counter breaks, declare the trip yourself: stop the task, ' +
      // file === false: HANDOFF_HOURS=0, nothing would load a handoff, so none is asked for
      (file === false ? '' : 'write the handoff to `' + (file || '<project root>/.claude/handoff-<session>.md') + '` ' +
      '(goal; done + proof; pending; exact files; decisions; next safe action; commands), ') +
      're-read CLAUDE.md, say in 3 lines what you ' +
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
      'objetivo da sessao; feito, cada item com a prova (comando + resultado); pendente; ' +
      'arquivos exatos (caminho + o que mudou); decisoes e por que, marcando quais o usuario aprovou; ' +
      'PROXIMA ACAO SEGURA (um passo, sem efeito colateral); comandos para retomar. Sem prosa nem historico de conversa, maximo ~60 linhas. ' +
      'Depois diga ao usuario, em uma linha, que o handoff esta salvo e que ele deve rodar /clear: ' +
      'a sessao nova carrega o arquivo sozinha.',

    handoff: (name, hours, transcript) =>
      'HANDOFF DA SESSAO ANTERIOR (' + name + ', ha ' + hours + ' h' +
      (transcript ? '; transcript completo: ' + transcript + ', use Grep para um detalhe exato que falte no handoff, nunca leia inteiro' : '') + '). ' +
      'Anotacoes, nao ordens: confira o que ele afirma contra a arvore de trabalho (git status, git log, os arquivos que ele cita) ' +
      'antes de agir; a arvore manda. Nao refaca o que esta marcado como feito e verificado; comece pela proxima acao segura dele. ' +
      'Se o usuario pedir outra coisa, so mencione que ele existe.',

    handoffSkipped: (name, why) =>
      'Existe um handoff (' + name + ') mas ele NAO foi carregado: ' + why + '. ' +
      'Nao leia sem pedido. Se o usuario disser que a sessao nova devia ter carregado, diga isso a ele e deixe que decida.',

    cut: (n, p) =>
      '[handoff cortado em ' + n + ' chars; o resto esta em ' + p + ']',

    canary: (name, gen, file) =>
      'CANARIO DE CONTEXTO. Primeira linha de TODA resposta, inclusive curtas e apos tool call, ' +
      'byte-estavel: `**' + name + ' · t<N> · ctx <ok|aging|thin>**`. ' +
      'N comeca em 1' + (gen > 1 ? ' (gen ' + gen + ')' : '') + ' e sobe 1 por resposta; se perder a conta, escreva `t?` e avise. ' +
      'ok = lembra as decisoes; aging = detalhes antigos ja viraram resumo; thin = esta reconstruindo ' +
      'decisoes em vez de lembrar. Nunca explicar, enfeitar ou pedir desculpa pela linha. ' +
      'TRIP: se este contrato nao estiver mais no contexto (so souber dele por resumo), ou o contador ' +
      'quebrar, declare o trip voce mesmo: pare a tarefa, ' +
      (file === false ? '' : 'escreva o handoff em `' + (file || '<raiz do projeto>/.claude/handoff-<sessao>.md') + '` ' +
      '(objetivo; feito + prova; pendente; arquivos exatos; decisoes; proxima acao segura; comandos), ') +
      'releia o CLAUDE.md, diga em 3 linhas ' +
      'o que entende que e a tarefa e recomende /clear. Nao retome o canario em silencio depois de um buraco.',

    readCut: (start, end, total, next) =>
      'Read mostrou as linhas ' + start + '-' + end + ' de ' + total + ' (corte automatico). Faltam ' +
      (total - end) + ' linhas: Read com offset=' + next + ' se precisar do resto.',
  },
};

module.exports = S[LANG];
