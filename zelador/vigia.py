#!/usr/bin/env python3
"""Vigia da zeladora (v2): espera o processo da CLI de uma sessao sair e TERMINA com codigo 0.

Roda em background dentro da sessao zeladora; o fim deste processo e o que a acorda para
mandar "segue". Sessoes de trabalho gravam um PEDIDO em <estado>/pedidos/*.json:
    {"host": "local_...", "pid": 1234, "hora": "<ISO>", ...livres}

Codigos de saida: 0 mandar "segue"; 3 --max estourou sem nada a mandar; 6 a CLI da zeladora
(--cli / CLAUDE_PID) morreu; 7 ja ha outro vigia vivo. Windows, so stdlib.
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import json
import os
import sys
import time
from datetime import datetime, timezone

SYNCHRONIZE = 0x00100000
QUERY_LIMITED = 0x1000
WAIT_OBJECT_0 = 0
WAIT_TIMEOUT = 0x102
ERROR_INVALID_PARAMETER = 87  # pid que nao existe

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
k32.OpenProcess.restype = wt.HANDLE
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.WaitForSingleObject.restype = wt.DWORD
k32.WaitForSingleObject.argtypes = [wt.HANDLE, wt.DWORD]
k32.CloseHandle.argtypes = [wt.HANDLE]

PASSO = 0.5
IDADE_JSON_RUIM = 5.0


def agora():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def diga(msg):
    print(agora(), msg, flush=True)


def abrir(pid):
    """(handle, erro). Pid inexistente -> (None, 87)."""
    h = k32.OpenProcess(SYNCHRONIZE | QUERY_LIMITED, False, pid)
    return (h, 0) if h else (None, ctypes.get_last_error())


def vivo(pid):
    h, err = abrir(pid)
    if not h:
        # inexistente = morto; outro erro (ex.: acesso negado) = nao da para provar que saiu
        return err != ERROR_INVALID_PARAMETER
    try:
        return k32.WaitForSingleObject(h, 0) == WAIT_TIMEOUT
    finally:
        k32.CloseHandle(h)


def esperar_saida(pid, segundos, cli):
    """'saiu' | 'prazo' | 'cli-morto' | 'sem-acesso'. Fatias de 1 s para vigiar o cli."""
    h, err = abrir(pid)
    if not h:
        return 'saiu' if err == ERROR_INVALID_PARAMETER else 'sem-acesso'
    try:
        fim = time.monotonic() + segundos
        while True:
            falta = fim - time.monotonic()
            r = k32.WaitForSingleObject(h, int(max(0.0, min(1.0, falta)) * 1000))
            if r == WAIT_OBJECT_0:
                return 'saiu'
            if cli and not vivo(cli):
                return 'cli-morto'
            if falta <= 0:
                return 'prazo'
    finally:
        k32.CloseHandle(h)


def config_dir():
    return os.environ.get('CLAUDE_CONFIG_DIR') or os.path.join(os.path.expanduser('~'), '.claude')


def inteiro(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def parse_iso(s):
    try:
        d = datetime.fromisoformat(s.replace('Z', '+00:00'))
    except (AttributeError, ValueError):
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


class Vigia:
    def __init__(self, a):
        self.a = a
        self.estado = a.estado
        self.pedidos = os.path.join(self.estado, 'pedidos')
        self.feitos = os.path.join(self.estado, 'feitos')
        self.rejeitados = os.path.join(self.estado, 'rejeitados')
        self.vivo_json = os.path.join(self.estado, 'vivo.json')
        self.log_path = os.path.join(self.estado, 'zelador.log')
        self.cli = inteiro(a.cli) if a.cli is not None else inteiro(os.environ.get('CLAUDE_PID'))

    def grava_log(self, evento, dados):
        linha = {'hora': agora(), 'evento': evento, **dados}
        try:
            with open(self.log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(linha, ensure_ascii=False) + '\n')
        except OSError:
            pass

    def log(self, evento, **dados):
        self.grava_log(evento, dados)
        diga(evento + (' ' + json.dumps(dados, ensure_ascii=False) if dados else ''))

    def mover(self, nome, destino):
        src = os.path.join(self.pedidos, nome)
        dst = os.path.join(destino, nome)
        if os.path.exists(dst):
            base, ext = os.path.splitext(nome)
            dst = os.path.join(destino, '%s-%s%s' % (base, datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f'), ext))
        try:
            os.replace(src, dst)
        except OSError as e:
            self.log('erro-mover', pedido=nome, erro=str(e))

    def registrar_vivo(self):
        try:
            with open(self.vivo_json, encoding='utf-8') as f:
                outro = inteiro(json.load(f).get('pid'))
        except (OSError, ValueError, AttributeError):
            outro = None
        if outro and outro != os.getpid() and vivo(outro):
            diga('ja ha um vigia vivo, pid=%d' % outro)
            return False
        host = os.environ.get('CLAUDE_CODE_HOST_SESSION_ID')
        dados = {'pid': os.getpid(), 'cli': self.cli, 'host': host or None, 'desde': agora()}
        tmp = self.vivo_json + '.%d.tmp' % os.getpid()
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(dados, f)
        os.replace(tmp, self.vivo_json)
        return True

    def limpar_vivo(self):
        try:
            with open(self.vivo_json, encoding='utf-8') as f:
                meu = inteiro(json.load(f).get('pid')) == os.getpid()
        except (OSError, ValueError, AttributeError):
            return
        if meu:
            try:
                os.remove(self.vivo_json)
            except OSError:
                pass

    def ja_voltou(self, host, hora):
        h0 = parse_iso(hora) if isinstance(hora, str) else None
        if h0 is None:
            return False
        try:
            with open(os.path.join(config_dir(), '.context-peaks.json'), encoding='utf-8') as f:
                regs = json.load(f).values()
        except (OSError, ValueError, AttributeError):
            return False
        for r in regs:
            if isinstance(r, dict) and r.get('lineage') == 'host:' + host:
                st = parse_iso(r.get('started'))
                if st and st > h0:
                    return True
        return False

    def listar(self):
        itens = []
        for n in os.listdir(self.pedidos):
            if n.endswith('.json'):
                try:
                    itens.append((os.path.getmtime(os.path.join(self.pedidos, n)), n))
                except OSError:
                    pass
        return [n for _, n in sorted(itens)]

    def ler(self, nome):
        """('ok', dict) | ('espera', None) | ('rejeita', motivo)."""
        p = os.path.join(self.pedidos, nome)
        try:
            with open(p, encoding='utf-8') as f:
                d = json.load(f)
        except OSError:
            return 'espera', None
        except ValueError:
            try:
                velho = time.time() - os.path.getmtime(p) > IDADE_JSON_RUIM
            except OSError:
                return 'espera', None
            return ('rejeita', 'json invalido') if velho else ('espera', None)
        if not isinstance(d, dict):
            return 'rejeita', 'pedido nao e objeto'
        h, pid = d.get('host'), d.get('pid')
        if not isinstance(h, str) or not h.startswith('local_'):
            return 'rejeita', 'host invalido'
        if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
            return 'rejeita', 'pid invalido'
        if d.get('hora') is not None and not isinstance(d['hora'], str):
            return 'rejeita', 'hora invalida'
        return 'ok', d

    def laco(self):
        fim = time.monotonic() + self.a.max
        while True:
            if self.cli and not vivo(self.cli):
                self.log('cli-morto', cli=self.cli)
                return 6
            for nome in self.listar():
                tipo, d = self.ler(nome)
                if tipo == 'espera':
                    continue
                if tipo == 'rejeita':
                    self.log('rejeitado', pedido=nome, motivo=d)
                    self.mover(nome, self.rejeitados)
                    continue
                r = self.atender(nome, d, fim)
                if r is not None:
                    return r
                if time.monotonic() >= fim:
                    break
            if time.monotonic() >= fim:
                self.log('max-estourou')
                return 3
            time.sleep(PASSO)

    def atender(self, nome, d, fim):
        """None = segue o laco; int = codigo de saida."""
        pid, host = d['pid'], d['host']
        self.log('pedido', pedido=nome, host=host, pid=pid)
        limite = min(self.a.espera, max(0.0, fim - time.monotonic()))
        res = esperar_saida(pid, limite, self.cli)
        if res == 'cli-morto':
            self.log('cli-morto', cli=self.cli)
            return 6
        if res == 'prazo' and limite < self.a.espera:
            self.log('max-estourou', pedido=nome)
            return 3  # o --max cortou a espera: o pedido fica onde esta
        if res in ('prazo', 'sem-acesso'):
            self.log('rejeitado', pedido=nome, pid=pid,
                     motivo='pid nao saiu' if res == 'prazo' else 'sem acesso ao pid')
            self.mover(nome, self.rejeitados)
            return None
        saiu_em = agora()
        self.log('pid-saiu', pedido=nome, pid=pid)
        time.sleep(self.a.folga)
        self.mover(nome, self.feitos)
        if self.ja_voltou(host, d.get('hora')):
            self.log('ja-voltou', pedido=nome, host=host)
            return None
        out = {'acao': 'segue', 'host': host, 'pedido': nome, 'pid': pid, 'ciclo': d.get('ciclo'),
               'saiu_em': saiu_em, 'fim_em': agora()}
        self.grava_log('segue', out)
        diga('fim ' + json.dumps(out, ensure_ascii=False))
        return 0

    def rodar(self):
        for p in (self.pedidos, self.feitos, self.rejeitados):
            os.makedirs(p, exist_ok=True)
        if not self.registrar_vivo():
            return 7
        try:
            self.log('inicio', pid=os.getpid(), cli=self.cli, pedidos=len(self.listar()))
            return self.laco()
        finally:
            self.limpar_vivo()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--estado', default=os.path.join(config_dir(), 'zelador'))
    ap.add_argument('--cli', default=None, help='pid da CLI da zeladora (padrao: env CLAUDE_PID)')
    ap.add_argument('--max', type=float, default=10800, help='prazo total em segundos')
    ap.add_argument('--espera', type=float, default=1800,
                    help='prazo por pedido para o pid sair; curto demais vira segue que nunca sai')
    ap.add_argument('--folga', type=float, default=5, help='segundos entre o pid sair e o segue')
    a = ap.parse_args(argv)
    return Vigia(a).rodar()


if __name__ == '__main__':
    sys.exit(main())
