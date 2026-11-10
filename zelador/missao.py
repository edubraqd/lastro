#!/usr/bin/env python3
"""Missao do zelador: arma, conclui e mostra a missao de uma sessao do app desktop.

    python missao.py armar [--arquivo F] [--max-ciclos 10] [--min-ctx 150000]   (sem --arquivo: texto pelo stdin)
    python missao.py concluir
    python missao.py status

A sessao e a do app (CLAUDE_CODE_HOST_SESSION_ID, ou --host). Com a missao armada e um vigia
vivo, os hooks do Lastro trocam "diga ao usuario para rodar /clear" por handoff +
clear_session("self"), e o hooks/clear-gate.js registra o pedido que o vigia atende.
Estado em <CLAUDE_CONFIG_DIR ou ~/.claude>/zelador/missoes/<host>.json. So stdlib.
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone


def raiz():
    base = os.environ.get('CLAUDE_CONFIG_DIR') or os.path.join(os.path.expanduser('~'), '.claude')
    return os.path.join(base, 'zelador')


def agora():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def vivo(pid):
    """os.kill(pid, 0) no Windows MATA o processo: aqui so se abre e se pergunta."""
    if os.name != 'nt':
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
    import ctypes
    import ctypes.wintypes as wt
    k32 = ctypes.WinDLL('kernel32', use_last_error=True)
    k32.OpenProcess.restype = wt.HANDLE
    k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
    k32.WaitForSingleObject.restype = wt.DWORD
    k32.WaitForSingleObject.argtypes = [wt.HANDLE, wt.DWORD]
    k32.CloseHandle.argtypes = [wt.HANDLE]
    h = k32.OpenProcess(0x00100000, False, pid)   # SYNCHRONIZE
    if not h:
        return ctypes.get_last_error() == 5       # acesso negado: existe
    try:
        return k32.WaitForSingleObject(h, 0) == 0x102   # WAIT_TIMEOUT: ainda rodando
    finally:
        k32.CloseHandle(h)


def ler(p):
    try:
        with open(p, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def gravar(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = '%s.%d.tmp' % (p, os.getpid())
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('acao', choices=['armar', 'concluir', 'status'])
    ap.add_argument('--host', default=os.environ.get('CLAUDE_CODE_HOST_SESSION_ID', ''))
    ap.add_argument('--arquivo', help='texto da missao (sem ele, vem do stdin)')
    ap.add_argument('--max-ciclos', type=int, default=10, help='teto de clears automaticos da missao')
    ap.add_argument('--min-ctx', type=int, default=150000, help='contexto minimo (tokens) para o clear automatico')
    a = ap.parse_args()
    if not re.fullmatch(r'local_[\w-]+', a.host):
        sys.exit('sem sessao do app: CLAUDE_CODE_HOST_SESSION_ID vazio ou fora do formato local_... (use --host)')
    p = os.path.join(raiz(), 'missoes', a.host + '.json')
    m = ler(p)
    v = ler(os.path.join(raiz(), 'vivo.json'))
    v = v if isinstance(v, dict) else {}
    pid, cli = v.get('pid'), v.get('cli')
    # o vigia acorda a zeladora ao terminar: com a CLI dela morta, ninguem seria acordado
    vigia = bool(isinstance(pid, int) and pid > 0 and vivo(pid)
                 and not (isinstance(cli, int) and cli > 0 and not vivo(cli)))

    if a.acao == 'armar':
        if a.arquivo:
            with open(a.arquivo, encoding='utf-8') as f:
                texto = f.read().strip()
        else:
            texto = sys.stdin.buffer.read().decode('utf-8').strip()
        if not texto:
            sys.exit('missao vazia: passe o texto pelo stdin ou por --arquivo')
        if a.max_ciclos < 1 or a.min_ctx < 0:
            sys.exit('--max-ciclos >= 1 e --min-ctx >= 0')
        m = {'host': a.host, 'estado': 'armada', 'criada': agora(), 'projeto': os.getcwd(), 'texto': texto,
             'ciclos': 0, 'max_ciclos': a.max_ciclos, 'min_ctx': a.min_ctx}
        gravar(p, m)
    elif a.acao == 'concluir':
        if not m:
            sys.exit('nenhuma missao desta sessao em ' + p)
        m.update(estado='concluida', concluida=agora())
        gravar(p, m)

    print(json.dumps({'host': a.host, 'estado': m['estado'] if m else None, 'ciclos': m.get('ciclos') if m else None,
                      'max_ciclos': m.get('max_ciclos') if m else None, 'min_ctx': m.get('min_ctx') if m else None,
                      'vigia_vivo': vigia, 'arquivo': p}, ensure_ascii=False))
    if a.acao == 'armar' and not vigia:
        print('AVISO: nenhum vigia vivo. Sem zelador o clear automatico e negado; suba o /zelador em outra sessao.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
