"""Gasto real dos workflows (ferramenta Workflow / ultracode) nesta maquina.

Fontes: ~/.claude/projects/<proj>/<sessao>/subagents/workflows/wf_*/ (journal + agent-*.jsonl),
a transcricao-mae <sessao>.jsonl (tool_use Workflow, tool_result com Run ID, task-notification)
e os scripts salvos em <sessao>/workflows/scripts/*-<runid>.js.
Preco e dedup: ledger.py do Lastro (D:/claude-context-forensics/tools), o mesmo que before_after.py importa.
Saida: texto no stdout + medir_workflows.json ao lado do script.
"""
import sys, os, re, json, glob, statistics, collections
sys.path.insert(0, r'D:\claude-context-forensics\tools')
import ledger  # noqa: E402  (prices, per_m_input, call_usd, load com dedup por (message.id, requestId))

PROJ = os.path.join(os.path.expanduser('~'), '.claude', 'projects')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'medir_workflows.json')
COST_TAGS = r'C:/Users/eduar/AppData/Local/Temp/claude/D--Clientes-Motor-2mil/0cfc1d2d-00bc-4bb6-b054-8dc0e26a1710/scratchpad/cost_tags.json'
SINCE = '2026-08-24'   # janela do cost_tags.py

seen = {}  # ledger.load (e056993) guarda a chamada por (message.id, requestId)


def usd_of(c):
    return sum(ledger.call_usd(c, ledger.prices(ledger.per_m_input(c['model']))).values())


def fam(model):
    m = model or ''
    for f in ('opus', 'sonnet', 'haiku'):
        if f in m:
            return m
    return m or '?'


def pct(xs, p):
    xs = sorted(xs)
    if not xs:
        return 0
    k = (len(xs) - 1) * p / 100
    lo = int(k); hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


# ---------------------------------------------------------------- 1. execucoes (pastas wf_*)
runs = {}
for wf in sorted(glob.glob(os.path.join(PROJ, '*', '*', 'subagents', 'workflows', 'wf_*'))):
    rid = os.path.basename(wf)
    sess_dir = os.path.dirname(os.path.dirname(os.path.dirname(wf)))
    proj = os.path.basename(os.path.dirname(sess_dir))
    sid = os.path.basename(sess_dir)
    started, results, labels, order = set(), {}, {}, []
    with open(os.path.join(wf, 'journal.jsonl'), encoding='utf-8', errors='replace') as f:
        for line in f:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d.get('type') == 'started':
                a = d['agentId']
                if a not in started:
                    order.append(a)
                started.add(a)
                if d.get('label') or d.get('phase'):
                    labels[a] = (d.get('label') or '', d.get('phase') or '')
            elif d.get('type') == 'result':
                results[d['agentId']] = d.get('result')
    agents = {}
    for a in order:
        p = os.path.join(wf, 'agent-%s.jsonl' % a)
        calls = ledger.load(p, seen, side=True) if os.path.exists(p) else []
        meta = {}
        mp = os.path.join(wf, 'agent-%s.meta.json' % a)
        if os.path.exists(mp):
            try:
                meta = json.load(open(mp, encoding='utf-8'))
            except ValueError:
                pass
        tok = {k: sum(c[k] for c in calls) for k in ('input', 'cw', 'cr', 'out')}
        bym = collections.defaultdict(float)
        for c in calls:
            bym[fam(c['model'])] += usd_of(c)
        agents[a] = dict(calls=calls, n=len(calls), tok=tok, usd=sum(bym.values()), bym=dict(bym),
                         usd_since=sum(usd_of(c) for c in calls if c['ts'][:10] >= SINCE),
                         ts=min((c['ts'] for c in calls), default=''), meta=meta,
                         label=labels.get(a, ('', ''))[0] or meta.get('description', ''),
                         phase=labels.get(a, ('', ''))[1] or meta.get('workflowPhase', ''),
                         has_result=a in results, result=results.get(a))
    runs[rid] = dict(rid=rid, proj=proj, sid=sid, sess_dir=sess_dir, agents=agents, order=order,
                     usd=sum(x['usd'] for x in agents.values()),
                     usd_since=sum(x['usd_since'] for x in agents.values()),
                     ts=min((x['ts'] for x in agents.values() if x['ts']), default=''))

# ---------------------------------------------------------------- 2. lancamentos na transcricao-mae
HUMAN_SKIP = ('<task-notification>', '<local-command-stdout>', '<local-command-stderr>', 'Caveat:')
EXPLICIT = re.compile(r'(?i)workflow|deep[- ]?research|sub-?agent|\bagentes?\b|\bagents?\b|multi-?agent|orquestr|em paralelo|in parallel|fan-?out|swarm')
cands = collections.defaultdict(list)   # tool_use_id -> uma entrada por copia da transcricao
launches = {}   # tool_use_id -> info escolhida
notif = {}      # tool_use_id -> status
exits = collections.Counter()   # arquivo -> n de ultra_effort_exit


def text_of(content):
    if isinstance(content, str):
        return content
    out = []
    for b in content or []:
        if isinstance(b, dict) and b.get('type') == 'text':
            out.append(b.get('text') or '')
    return '\n'.join(out)


wf_files = []
for p in glob.glob(os.path.join(PROJ, '*', '*.jsonl')):
    with open(p, encoding='utf-8', errors='replace') as f:
        for line in f:
            if '"name":"Workflow"' in line and '"tool_use"' in line:
                wf_files.append(p)
                break

for p in wf_files:
    sid_file = os.path.basename(p)[:-6]
    prompt = dict(text='', ts='', kw=False)
    ultra = False
    ultra_ever = False
    local = {}
    ultra_ts = ''
    with open(p, encoding='utf-8', errors='replace') as f:
        for line in f:
            quick = ('"type":"user"' in line or '"type":"attachment"' in line or '"Workflow"' in line
                     or 'task-notification' in line)
            if not quick:
                continue
            if '"tool_result"' in line and 'wf_' not in line and 'Workflow' not in line and 'task-notification' not in line:
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue
            t = d.get('type')
            if t == 'attachment':
                at = (d.get('attachment') or {})
                typ = at.get('type')
                if typ == 'ultra_effort_enter':
                    ultra = True; ultra_ever = True; ultra_ts = d.get('timestamp', '')
                elif typ == 'ultra_effort_exit':
                    ultra = False; exits[p] += 1
                elif typ == 'workflow_keyword_request':
                    prompt['kw'] = True
                elif typ == 'queued_command':
                    s = at.get('prompt') if isinstance(at.get('prompt'), str) else text_of(at.get('prompt'))
                    if s and not s.lstrip().startswith(HUMAN_SKIP):
                        prompt = dict(text=s, ts=d.get('timestamp', ''), kw='ultracode' in s.lower())
                    elif s and '<task-notification>' in s:
                        for m in re.finditer(r'<tool-use-id>(toolu_\w+)</tool-use-id>.*?<status>(\w+)</status>', s, re.S):
                            notif[m.group(1)] = m.group(2)
                continue
            m_ = d.get('message') if isinstance(d.get('message'), dict) else {}
            content = m_.get('content')
            if t == 'user':
                if isinstance(content, list) and any(isinstance(b, dict) and b.get('type') == 'tool_result' for b in content):
                    for b in content:
                        if isinstance(b, dict) and b.get('type') == 'tool_result' and b.get('tool_use_id') in local:
                            cc = b.get('content')
                            s = cc if isinstance(cc, str) else text_of(cc)
                            L = local[b['tool_use_id']]
                            if L.get('result') is None:
                                L['result'] = s[:3000]; L['is_error'] = bool(b.get('is_error'))
                    continue
                s = text_of(content)
                if '<task-notification>' in s:
                    for m in re.finditer(r'<tool-use-id>(toolu_\w+)</tool-use-id>.*?<status>(\w+)</status>', s, re.S):
                        notif[m.group(1)] = m.group(2)
                    continue
                if d.get('isMeta') or d.get('isCompactSummary') or not s.strip() or s.lstrip().startswith(HUMAN_SKIP):
                    continue
                prompt = dict(text=s, ts=d.get('timestamp', ''), kw='ultracode' in s.lower())
            elif t == 'assistant' and isinstance(content, list):
                for b in content:
                    if isinstance(b, dict) and b.get('type') == 'tool_use' and b.get('name') == 'Workflow':
                        rec = dict(id=b['id'], file=p, file_sid=sid_file, ts=d.get('timestamp', ''), input=b.get('input') or {},
                                   prompt=prompt['text'][:600], prompt_kw=prompt['kw'], ultra=ultra, ultra_ever=ultra_ever,
                                   ultra_ts=ultra_ts, result=None)
                        cands[b['id']].append(rec)
                        local[b['id']] = rec

# escolhe a copia: a da sessao dona do run (Transcript dir), senao a primeira com resultado
for tid, cs in cands.items():
    def owner(c):
        m = re.search(r'Transcript dir: (.+)', c.get('result') or '')
        return m and (os.sep + c['file_sid'] + os.sep) in m.group(1)
    launches[tid] = next((c for c in cs if owner(c)), None) or next((c for c in cs if c.get('result')), cs[0])

# liga lancamento -> run
launch_of_run = collections.defaultdict(list)
orphan_launch = []
errors = collections.Counter()
for L in launches.values():
    s = L.get('result') or ''
    m = re.search(r'Run ID: (wf_[0-9a-f-]+)', s)
    if not m:
        errors[(s[:70] if s else 'sem resultado')] += 1
        continue
    rid = m.group(1)
    L['rid'] = rid
    sp = re.search(r'Script file: (.+)', s)
    L['script_file'] = sp.group(1).strip() if sp else None
    L['status'] = notif.get(L['id'])
    launch_of_run[rid].append(L)
    if rid not in runs:
        orphan_launch.append(L)
for rid in launch_of_run:
    launch_of_run[rid].sort(key=lambda x: x['ts'])

# ---------------------------------------------------------------- 3. script, meta.name, tracos
def load_script(r):
    sd = r['sess_dir']
    fs = glob.glob(os.path.join(sd, 'workflows', 'scripts', '*-%s.js' % r['rid']))
    if fs:
        return open(fs[0], encoding='utf-8', errors='replace').read(), 'arquivo'
    for L in launch_of_run.get(r['rid'], []):
        if L['input'].get('script'):
            return L['input']['script'], 'inline'
        sf = L.get('script_file')
        if sf and os.path.exists(sf):
            return open(sf, encoding='utf-8', errors='replace').read(), 'arquivo'
    return '', 'nenhum'


def traits(src):
    tr = {}
    tr['agent_lit'] = len(re.findall(r'\bagent\s*\(', src))
    votes = re.findall(r'Array\.from\(\s*\{\s*length\s*:\s*([A-Za-z0-9_.]+)', src)
    tr['votes'] = len(votes)
    tr['while'] = len(re.findall(r'\bwhile\s*\(', src))
    tr['for'] = len(re.findall(r'\bfor\s*\((?:let|const|var)\b', src))
    tr['pipeline'] = len(re.findall(r'\bpipeline\s*\(', src))
    tr['parallel'] = len(re.findall(r'\bparallel\s*\(', src)) + len(re.findall(r'Promise\.all\s*\(', src))
    tr['map'] = len(re.findall(r'\.(?:map|flatMap)\s*\(', src))
    tr['model'] = re.findall(r"\bmodel\s*:\s*['\"](\w+)", src)
    tr['effort'] = re.findall(r"\beffort\s*:\s*['\"](\w+)", src)
    tr['worktree'] = len(re.findall(r"isolation\s*:\s*['\"]worktree", src))
    tr['verify'] = bool(re.search(r"(?i)(label|phase|title)\s*:\s*[`'\"][^`'\"]*(verif|refut|review|revis|c[eé]tic|juiz|j[uú]ri|adversar|skeptic|critic)", src))
    tr['agentType'] = re.findall(r"(?:agentType|subagent_type)\s*:\s*['\"]([\w:-]+)", src)
    return tr


for r in runs.values():
    src, how = load_script(r)
    r['script_src'] = how
    m = re.search(r"export\s+const\s+meta\s*=\s*\{.*?\bname\s*:\s*['\"`]([^'\"`]+)", src, re.S)
    md = re.search(r"export\s+const\s+meta\s*=\s*\{.*?\bdescription\s*:\s*['\"`]([^'\"`]+)", src, re.S)
    Ls = launch_of_run.get(r['rid'], [])
    named = next((L['input'].get('name') for L in Ls if L['input'].get('name')), None)
    r['name'] = (m.group(1) if m else None) or named or '?'
    r['desc'] = (md.group(1) if md else '') or next((L['input'].get('description', '') for L in Ls), '')
    r['named_wf'] = named
    r['tr'] = traits(src) if src else None
    r['launches'] = len(Ls)
    r['resume'] = sum(1 for L in Ls if L['input'].get('resumeFromRunId'))
    r['status'] = [L.get('status') for L in Ls]
    first = Ls[0] if Ls else None
    if first is None:
        r['origin'] = 'sem lancamento'
    elif first['prompt_kw']:
        r['origin'] = 'palavra ultracode no turno'
    elif first['ultra']:
        r['origin'] = 'ultracode ligado na sessao'
    elif EXPLICIT.search(first['prompt'] or '') or named:
        r['origin'] = 'pedido explicito'
    else:
        r['origin'] = 'indeterminado'
    r['prompt'] = first['prompt'][:300] if first else ''
    r['first'] = first
    r['ultra_ever'] = bool(first and first['ultra_ever'])

R = sorted(runs.values(), key=lambda r: r['ts'])
NA = [len(r['agents']) for r in R]

# ---------------------------------------------------------------- relatorio
def P(*a):
    print(*a)


P('== 0. reconciliacao')
P('transcricoes-mae com tool_use Workflow:', len(wf_files), '| tool_use Workflow unicos (por id):', len(launches))
P('lancamentos com Run ID:', sum(len(v) for v in launch_of_run.values()), '| run ids unicos:', len(launch_of_run),
  '| relancados com resumeFromRunId:', sum(1 for v in launch_of_run.values() if any(L['input'].get('resumeFromRunId') for L in v)))
P('recusados antes de rodar:', dict(errors))
P('pastas wf_* (journal):', len(runs), '| run ids sem pasta (sessao apagada/sem agente):', len({L['rid'] for L in orphan_launch}))
P('pastas sem lancamento achado:', sum(1 for r in R if not launch_of_run.get(r['rid'])))
P('script lido de:', dict(collections.Counter(r['script_src'] for r in R)))

P('\n== 1. execucoes')
P('N =', len(R), '| periodo', R[0]['ts'][:10], '->', R[-1]['ts'][:10])
byp = collections.defaultdict(list)
for r in R:
    byp[r['proj']].append(r)
for pj, rs in sorted(byp.items(), key=lambda kv: -len(kv[1]))[:8]:
    P('  %-50s runs=%3d agentes=%5d US$=%9.2f' % (pj[-50:], len(rs), sum(len(r['agents']) for r in rs), sum(r['usd'] for r in rs)))

P('\n== 2. agentes por execucao')
P('total agentes', sum(NA), '| mediana %.0f p75 %.0f p90 %.0f max %d media %.1f' % (pct(NA, 50), pct(NA, 75), pct(NA, 90), max(NA), sum(NA) / len(NA)))
bands = [(1, 3), (4, 9), (10, 19), (20, 49), (50, 10**9)]
for lo, hi in bands:
    rs = [r for r in R if lo <= len(r['agents']) <= hi]
    P('  faixa %-6s runs=%3d  US$=%9.2f  (%.0f%% do US$)' % ('%d-%s' % (lo, hi if hi < 10**9 else '+'), len(rs), sum(r['usd'] for r in rs),
                                                            100 * sum(r['usd'] for r in rs) / sum(r['usd'] for r in R)))

small = [r for r in R if len(r['agents']) <= 3]
P('  runs de 1-3 agentes: %d com 1 agente (US$ %.2f), %d com 2-3' % (sum(1 for r in small if len(r['agents']) == 1),
    sum(r['usd'] for r in small if len(r['agents']) == 1), sum(1 for r in small if len(r['agents']) > 1)))
P('\n== 3. tokens e US$')
tot = collections.Counter(); bym = collections.defaultdict(float); ncalls = 0
agent_usd = []
for r in R:
    for a in r['agents'].values():
        for k, v in a['tok'].items():
            tot[k] += v
        for k, v in a['bym'].items():
            bym[k] += v
        ncalls += a['n']
        agent_usd.append(a['usd'])
U = sum(r['usd'] for r in R)
P('chamadas (dedup message.id+requestId):', ncalls)
P('tokens: input %d | cache_write %d | cache_read %d | output %d' % (tot['input'], tot['cw'], tot['cr'], tot['out']))
P('US$ total workflows: %.2f' % U)
ru = [r['usd'] for r in R]
P('US$/execucao: mediana %.2f p75 %.2f p90 %.2f max %.2f media %.2f' % (pct(ru, 50), pct(ru, 75), pct(ru, 90), max(ru), U / len(R)))
P('US$/agente: mediana %.3f p90 %.3f media %.3f' % (pct(agent_usd, 50), pct(agent_usd, 90), U / len(agent_usd)))
tk = collections.Counter()
for r in R:
    for a in r['agents'].values():
        for c in a['calls']:
            pr = ledger.call_usd(c, ledger.prices(ledger.per_m_input(c['model'])))
            for k, v in pr.items():
                tk[k] += v
P('US$ por tipo de token:', {k: round(v, 2) for k, v in tk.items()})
fc = [a['calls'][0] for r in R for a in r['agents'].values() if a['calls']]
P('1a chamada de cada agente: contexto (input+cw+cr) mediana %.0f tok | US$ mediana %.3f | soma US$ %.2f (%.0f%% do US$)' % (
    pct([c['input'] + c['cw'] + c['cr'] for c in fc], 50), pct([usd_of(c) for c in fc], 50), sum(usd_of(c) for c in fc), 100 * sum(usd_of(c) for c in fc) / U))
cpa = [a['n'] for r in R for a in r['agents'].values()]
P('chamadas por agente: mediana %.0f p90 %.0f max %d' % (pct(cpa, 50), pct(cpa, 90), max(cpa)))
ctxa = [max((c['input'] + c['cw'] + c['cr']) for c in a['calls']) for r in R for a in r['agents'].values() if a['calls']]
P('pico de contexto por agente: mediana %.0f p90 %.0f max %d tok' % (pct(ctxa, 50), pct(ctxa, 90), max(ctxa)))
import math
xs = [math.log(len(r['agents'])) for r in R]; ys = [math.log(max(r['usd'], 0.01)) for r in R]
mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys)); vx = sum((x - mx) ** 2 for x in xs); vy = sum((y - my) ** 2 for y in ys)
P('correlacao log(agentes) x log(US$) por run: r=%.2f, inclinacao %.2f' % (cov / math.sqrt(vx * vy), cov / vx))
for k, v in sorted(bym.items(), key=lambda kv: -kv[1]):
    P('  modelo %-28s US$ %9.2f (%.0f%%)' % (k, v, 100 * v / U))
# fracao das sessoes-mae e do periodo
if os.path.exists(COST_TAGS):
    ct = json.load(open(COST_TAGS, encoding='utf-8'))
    ctd = {x['sid']: x for x in ct}
    U_since = sum(r['usd_since'] for r in R)
    mothers = {r['sid'] for r in R if r['usd_since'] > 0}
    mom_usd = sum(ctd[s]['usd'] for s in mothers if s in ctd)
    missing = [s for s in mothers if s not in ctd]
    per_usd = sum(x['usd'] for x in ct)
    P('cost_tags.json: %d sessoes, %s..%s, US$ %.2f' % (len(ct), min(x['start'] for x in ct)[:10], max(x['start'] for x in ct)[:10], per_usd))
    P('workflows com chamadas >= %s: US$ %.2f em %d sessoes-mae (%d fora do cost_tags)' % (SINCE, U_since, len(mothers), len(missing)))
    P('  fracao das sessoes-mae: %.1f%% (mae US$ %.2f) | fracao do periodo: %.1f%%' % (100 * U_since / mom_usd if mom_usd else 0, mom_usd, 100 * U_since / per_usd))

P('\n== 4. origem')
og = collections.defaultdict(list)
for r in R:
    og[r['origin']].append(r)
for k, rs in sorted(og.items(), key=lambda kv: -sum(r['usd'] for r in kv[1])):
    P('  %-30s runs=%3d agentes=%5d US$=%9.2f (%.0f%%) agentes/run med=%.0f' % (k, len(rs), sum(len(r['agents']) for r in rs), sum(r['usd'] for r in rs),
                                                                        100 * sum(r['usd'] for r in rs) / U, pct([len(r['agents']) for r in rs], 50)))
ol = collections.Counter()
for L in orphan_launch:
    ol['kw' if L['prompt_kw'] else 'ultra' if L['ultra'] else 'expl' if EXPLICIT.search(L['prompt'] or '') else 'indet'] += 1
P('  lancamentos sem pasta (sem custo medivel), origem:', dict(ol))
P('  ultracode ligado em algum momento antes do lancamento:', sum(1 for r in R if r['ultra_ever']), 'de', len(R))
uo = [r for r in R if r['origin'] == 'ultracode ligado na sessao']
ue = [r for r in uo if EXPLICIT.search(r['first']['prompt'] or '')]
P('  dentro de "ultracode ligado": prompt tambem cita workflow/agentes/paralelo: %d runs US$ %.2f | nao cita: %d runs US$ %.2f' % (
    len(ue), sum(r['usd'] for r in ue), len(uo) - len(ue), sum(r['usd'] for r in uo) - sum(r['usd'] for r in ue)))
from datetime import datetime as _dt


def _h(a, b):
    try:
        return (_dt.fromisoformat(b.replace('Z', '+00:00')) - _dt.fromisoformat(a.replace('Z', '+00:00'))).total_seconds() / 3600
    except ValueError:
        return None


gaps = [g for g in (_h(r['first']['ultra_ts'], r['first']['ts']) for r in uo if r['first']['ultra_ts']) if g is not None]
P('  horas entre o ultimo lembrete ultra_effort_enter e o lancamento: mediana %.2f p90 %.2f max %.1f' % (pct(gaps, 50), pct(gaps, 90), max(gaps)))
P('  ultra_effort_exit nas transcricoes-mae: %d eventos em %d arquivos; sessoes-mae com workflow: %d' % (sum(exits.values()), len(exits), len({r['sid'] for r in R})))

P('\n== 5. tracos do script')
withtr = [r for r in R if r['tr']]
P('runs com script lido:', len(withtr))
lit = [r['tr']['agent_lit'] for r in withtr]
mult = [len(r['agents']) / r['tr']['agent_lit'] for r in withtr if r['tr']['agent_lit']]
P('agent() literais/script: mediana %.0f p90 %.0f max %d | agentes reais / literais: mediana %.1f p90 %.1f max %.1f' % (
    pct(lit, 50), pct(lit, 90), max(lit), pct(mult, 50), pct(mult, 90), max(mult)))


def grp(name, pred):
    a = [r for r in withtr if pred(r)]
    b = [r for r in withtr if not pred(r)]
    f = lambda rs: (len(rs), pct([len(r['agents']) for r in rs], 50), pct([r['usd'] for r in rs], 50), sum(r['usd'] for r in rs))
    P('  %-34s com: n=%3d ag_med=%4.0f US$_med=%7.2f US$=%8.2f | sem: n=%3d ag_med=%4.0f US$_med=%7.2f US$=%8.2f' % ((name,) + f(a) + f(b)))


grp('votos Array.from({length})', lambda r: r['tr']['votes'] > 0)
grp('while', lambda r: r['tr']['while'] > 0)
grp('pipeline()', lambda r: r['tr']['pipeline'] > 0)
grp('parallel()/Promise.all', lambda r: r['tr']['parallel'] > 0)
grp('.map() (fan-out por lista)', lambda r: r['tr']['map'] > 0)
grp('fase de verificacao/refutacao', lambda r: r['tr']['verify'])
grp('model: setado', lambda r: bool(r['tr']['model']))
grp('effort: setado', lambda r: bool(r['tr']['effort']))
grp('isolation worktree', lambda r: r['tr']['worktree'] > 0)
grp('workflow nomeado (name/args)', lambda r: bool(r['named_wf']))
P('  model setado:', collections.Counter(m for r in withtr for m in r['tr']['model']), '| effort:', collections.Counter(m for r in withtr for m in r['tr']['effort']))
P('  agentType no script:', collections.Counter(m for r in withtr for m in r['tr']['agentType']).most_common(6))
P('  agentType real (meta.json):', collections.Counter(a['meta'].get('agentType') for r in R for a in r['agents'].values()).most_common(6))
# papel por fase: verificadores x resto
VER = re.compile(r'(?i)verif|refut|review|revis|c[eé]tic|juiz|j[uú]ri|jury|adversar|skeptic|critic|cr[ií]tic|confer|\bref\d*\b|^ref')


def is_verifier(a):
    if VER.search((a['label'] or '') + ' ' + (a['phase'] or '')):
        return True
    res = a['result']
    return isinstance(res, dict) and bool({'refuted', 'refutado', 'refutada', 'real', 'verdict', 'veredito'} & set(res))


ver_usd = sum(a['usd'] for r in R for a in r['agents'].values() if is_verifier(a))
ver_n = sum(1 for r in R for a in r['agents'].values() if is_verifier(a))
P('  agentes verificadores/revisores: %d (%.0f%% dos agentes), US$ %.2f (%.0f%% do US$)' % (ver_n, 100 * ver_n / sum(NA), ver_usd, 100 * ver_usd / U))

P('\n== 6. top 10 mais caras')
top = sorted(R, key=lambda r: -r['usd'])[:10]
for r in top:
    P('  %s %-40s %-28s ag=%3d US$=%7.2f lit=%s orig=%s' % (r['ts'][:10], r['proj'][-40:], r['name'][:28], len(r['agents']), r['usd'],
                                                          r['tr']['agent_lit'] if r['tr'] else '?', r['origin']))
    P('       desc:', (r['desc'] or '')[:160].replace('\n', ' '))
    P('       prompt:', (r['prompt'] or '')[:220].replace('\n', ' '))
    ph = collections.Counter((a['phase'] or a['label'].split(':')[0] or '-') for a in r['agents'].values())
    P('       fases:', dict(ph.most_common(8)))
    au = sorted((a['usd'] for a in r['agents'].values()), reverse=True)
    vu = sum(a['usd'] for a in r['agents'].values() if is_verifier(a))
    P('       chamadas/agente med=%.0f | US$ agente max=%.2f med=%.2f | US$ verificadores=%.2f (%.0f%%) | modelos=%s' % (
        pct([a['n'] for a in r['agents'].values()], 50), au[0], pct(au, 50), vu, 100 * vu / r['usd'] if r['usd'] else 0,
        dict(collections.Counter(c['model'] for a in r['agents'].values() for c in a['calls']).most_common(3))))
P('  top10 = %.0f%% do US$ dos workflows' % (100 * sum(r['usd'] for r in top) / U))

P('\n== 7. desperdicio mensuravel')
ab = [(r, a) for r in R for a in r['agents'].values() if not a['has_result']]
P('agentes sem resultado no journal (abortados/morreram): %d, US$ %.2f, em %d runs' % (len(ab), sum(a['usd'] for _, a in ab), len({r['rid'] for r, _ in ab})))
nul = [(r, a) for r in R for a in r['agents'].values() if a['has_result'] and (a['result'] in (None, '', {}, []))]
P('resultado vazio/null: %d, US$ %.2f' % (len(nul), sum(a['usd'] for _, a in nul)))
errs = [(r, a) for r in R for a in r['agents'].values() if isinstance(a['result'], str) and re.match(r'(?i)\s*(SECURITY WARNING|error|api error|agent (failed|aborted)|failed)', a['result'])]
P('resultado string de erro/aviso: %d, US$ %.2f' % (len(errs), sum(a['usd'] for _, a in errs)))


def shingles(s, k=5):
    w = re.findall(r'\w+', s.lower())
    return {' '.join(w[i:i + k]) for i in range(max(0, len(w) - k + 1))}


dup = []
for r in R:
    items = []
    for aid in r['order']:
        a = r['agents'][aid]
        if not a['has_result'] or a['result'] is None:
            continue
        s = a['result'] if isinstance(a['result'], str) else json.dumps(a['result'], ensure_ascii=False, sort_keys=True)
        if len(re.findall(r'\w+', s)) < 40:
            continue
        items.append((aid, shingles(s)))
    marked = set()
    for i in range(len(items)):
        for j in range(i):
            if items[j][0] in marked:
                continue
            A, B = items[i][1], items[j][1]
            if A and B and len(A & B) / len(A | B) >= 0.8:
                marked.add(items[i][0])
                break
    for aid in marked:
        dup.append((r, r['agents'][aid]))
P('resultados quase identicos a outro do mesmo run (Jaccard 5-gramas >= 0,8): %d agentes, US$ %.2f, em %d runs' % (
    len(dup), sum(a['usd'] for _, a in dup), len({r['rid'] for r, _ in dup})))

CORR = re.compile(r'(?i)correct|correc|corrig|problem|issue|discrep|missing|achados_novos|fatais|findings_refuted')
PASSV = {'refuted': False, 'refutado': False, 'refutada': False, 'real': True, 'ok': True}


def verifier_class(res):
    if not isinstance(res, dict):
        return 'texto'
    hit = None
    for k, v in PASSV.items():
        if k in res and isinstance(res[k], bool):
            hit = (res[k] == v)
            break
    if hit is None and isinstance(res.get('verdict'), str):
        hit = res['verdict'].lower() in ('confirmed', 'confirmado', 'pass', 'ok', 'valid')
    if hit is None:
        return 'sem campo de veredito'
    if not hit:
        return 'refutou/achou problema'
    corr = [v for k, v in res.items() if CORR.search(k)]
    if any(v not in (None, '', [], {}, False, 'none', 'None', 'n/a', 'N/A', '-') for v in corr):
        return 'confirmou com correcao'
    return 'so confirmou'


vc = collections.defaultdict(lambda: [0, 0.0])
for r in R:
    for a in r['agents'].values():
        if is_verifier(a) and a['has_result']:
            k = verifier_class(a['result'])
            vc[k][0] += 1; vc[k][1] += a['usd']
P('verificadores por desfecho:', {k: (n, round(u, 2)) for k, (n, u) in sorted(vc.items(), key=lambda kv: -kv[1][1])})
rel = [r for r in R if r['launches'] > 1 or r['resume']]
P('runs relancados (mesmo Run ID, resumeFromRunId): %d, US$ total desses runs %.2f' % (len(rel), sum(r['usd'] for r in rel)))
for r in rel:
    t2 = launch_of_run[r['rid']][-1]['ts']
    pre = [a for a in r['agents'].values() if a['ts'] and a['ts'] < t2]
    pos = [a for a in r['agents'].values() if a['ts'] and a['ts'] >= t2]
    P('    %s %s: antes do resume %d agentes US$ %.2f (sem resultado: %d, US$ %.2f) | depois %d agentes US$ %.2f' % (
        r['name'], r['ts'][:10], len(pre), sum(a['usd'] for a in pre), sum(1 for a in pre if not a['has_result']),
        sum(a['usd'] for a in pre if not a['has_result']), len(pos), sum(a['usd'] for a in pos)))
# mesmo meta.name relancado na mesma sessao
same = collections.defaultdict(list)
for r in R:
    same[(r['sid'], r['name'])].append(r)
again = [(k, rs) for k, rs in same.items() if len(rs) > 1 and k[1] != '?']
P('mesmo meta.name lancado de novo na mesma sessao: %d grupos, %d runs extras, US$ dos extras %.2f' % (
    len(again), sum(len(rs) - 1 for _, rs in again), sum(sum(r['usd'] for r in sorted(rs, key=lambda r: r['ts'])[1:]) for _, rs in again)))
for k, rs in sorted(again, key=lambda kv: -sum(r['usd'] for r in kv[1]))[:6]:
    P('    %s x%d US$ %s status=%s' % (k[1], len(rs), [round(r['usd'], 2) for r in sorted(rs, key=lambda r: r['ts'])],
                                       [r['status'] for r in sorted(rs, key=lambda r: r['ts'])]))
st = collections.Counter(s for r in R for s in r['status'])
P('status das task-notifications:', dict(st))
bad = [r for r in R if r['status'] and r['status'][-1] in ('failed', 'killed', 'error', 'stopped', 'cancelled')]
P('runs cujo ultimo status nao foi completed: %d, US$ %.2f' % (len(bad), sum(r['usd'] for r in bad)))

P('\n== 8. fan-out fora do Workflow (ferramenta Agent)')
ag_files = [f for f in glob.glob(os.path.join(PROJ, '*', '*', 'subagents', '**', 'agent-*.jsonl'), recursive=True)
            if os.sep + 'workflows' + os.sep not in f]
per_sess = collections.defaultdict(lambda: [0, 0.0, 0.0])
ag_usd = []
types = collections.Counter()
for f in ag_files:
    calls = ledger.load(f, seen, side=True)
    u = sum(usd_of(c) for c in calls)
    us = sum(usd_of(c) for c in calls if c['ts'][:10] >= SINCE)
    sess = f.split(os.sep + 'subagents' + os.sep)[0]
    per_sess[sess][0] += 1; per_sess[sess][1] += u; per_sess[sess][2] += us
    ag_usd.append(u)
    mp = f[:-6] + '.meta.json'
    try:
        types[json.load(open(mp, encoding='utf-8')).get('agentType')] += 1
    except (OSError, ValueError):
        types['(sem meta)'] += 1
cnt = [v[0] for v in per_sess.values()]
AU = sum(v[1] for v in per_sess.values())
P('subagentes Agent: %d em %d sessoes | por sessao: mediana %.0f p90 %.0f max %d' % (len(ag_files), len(per_sess), pct(cnt, 50), pct(cnt, 90), max(cnt)))
P('US$ total Agent: %.2f | US$/subagente mediana %.3f media %.3f | US$/sessao mediana %.2f' % (
    AU, pct(ag_usd, 50), AU / len(ag_usd), pct([v[1] for v in per_sess.values()], 50)))
P('tipos:', types.most_common(6))
if os.path.exists(COST_TAGS):
    AUs = sum(v[2] for v in per_sess.values())
    P('Agent com chamadas >= %s: US$ %.2f (%.1f%% do periodo do cost_tags) vs workflows %.2f (%.1f%%)' % (
        SINCE, AUs, 100 * AUs / per_usd, U_since, 100 * U_since / per_usd))
wf_sess = {os.path.join(PROJ, r['proj'], r['sid']) for r in R}
both = [v for s, v in per_sess.items() if s in wf_sess]
P('sessoes que tambem rodaram workflow: %d, subagentes Agent nelas %d, US$ %.2f' % (len(both), sum(v[0] for v in both), sum(v[1] for v in both)))

# ---------------------------------------------------------------- json
dump = [dict(rid=r['rid'], proj=r['proj'], sid=r['sid'], ts=r['ts'], name=r['name'], desc=r['desc'], agents=len(r['agents']),
             usd=round(r['usd'], 3), origin=r['origin'], tr=r['tr'], prompt=r['prompt'], status=r['status'], resume=r['resume'])
        for r in R]
json.dump(dump, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
P('\njson:', OUT)
