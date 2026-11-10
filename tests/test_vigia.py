#!/usr/bin/env python3
"""Vigia da zeladora: processos de verdade, timers curtos por flag.

    python -m unittest tests.test_vigia -v

Windows. CLAUDE_CONFIG_DIR falso em tempdir; nada em ~/.claude.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIGIA = os.path.join(REPO, 'zelador', 'vigia.py')
LEAK = ('CLAUDE_CODE_HOST_SESSION_ID', 'CLAUDE_PID', 'CLAUDE_CONFIG_DIR')


def iso(delta=0):
    return (datetime.now(timezone.utc) + timedelta(seconds=delta)).isoformat().replace('+00:00', 'Z')


class VigiaTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='ccf-vigia-')
        self.cfg = os.path.join(self.tmp, 'claude')
        self.estado = os.path.join(self.tmp, 'estado')
        os.makedirs(self.cfg)
        self.procs = []
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.addCleanup(self._matar)

    def _matar(self):
        for p in self.procs:
            if p.poll() is None:
                p.kill()
            p.wait()
            if p.stdout:
                p.stdout.close()

    def pasta(self, nome):
        return os.path.join(self.estado, nome)

    def vigia(self, *flags):
        env = {k: v for k, v in os.environ.items() if k not in LEAK}
        env['CLAUDE_CONFIG_DIR'] = self.cfg
        p = subprocess.Popen([sys.executable, '-I', VIGIA, '--estado', self.estado, *flags],
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', env=env)
        self.procs.append(p)
        return p

    def dormir(self, s):
        p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(%s)' % s])
        self.procs.append(p)
        return p

    def pedido(self, nome, obj):
        d = self.pasta('pedidos')
        os.makedirs(d, exist_ok=True)
        tmp = os.path.join(d, nome + '.tmp')
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(obj, f)
        os.replace(tmp, os.path.join(d, nome))

    def esperar_vivo(self):
        fim = time.monotonic() + 10
        while time.monotonic() < fim:
            if os.path.exists(os.path.join(self.estado, 'vivo.json')):
                return
            time.sleep(0.1)
        self.fail('vigia nao subiu')

    def terminar(self, v, timeout=40):
        out, _ = v.communicate(timeout=timeout)
        return out

    def fim(self, out):
        linha = out.strip().splitlines()[-1]
        self.assertIn(' fim ', linha)
        return json.loads(linha.split(' fim ', 1)[1])

    def lista(self, nome):
        d = self.pasta(nome)
        return sorted(os.listdir(d)) if os.path.isdir(d) else []

    def sem_vivo(self):
        self.assertFalse(os.path.exists(os.path.join(self.estado, 'vivo.json')))

    def test_1_pid_vivo_so_termina_depois_de_sair_mais_folga(self):
        v = self.vigia('--folga', '1', '--max', '30')
        self.esperar_vivo()
        s = self.dormir(3)
        t0 = time.monotonic()
        self.pedido('p.json', {'host': 'local_a', 'pid': s.pid, 'ciclo': 2})
        out = self.terminar(v)
        dt = time.monotonic() - t0
        self.assertEqual(v.returncode, 0, out)
        self.assertGreaterEqual(dt, 3.9, out)  # ~3 s do pid + 1 s de folga
        self.assertIsNotNone(s.poll())
        res = self.fim(out)
        self.assertEqual((res['acao'], res['host'], res['pid'], res['ciclo'], res['pedido']),
                         ('segue', 'local_a', s.pid, 2, 'p.json'))
        self.assertIn('saiu_em', res)
        self.assertIn('fim_em', res)
        self.assertEqual(self.lista('feitos'), ['p.json'])
        self.assertEqual(self.lista('pedidos'), [])
        self.sem_vivo()
        with open(os.path.join(self.estado, 'zelador.log'), encoding='utf-8') as f:
            eventos = [json.loads(x) for x in f if x.strip()]
        self.assertTrue(all('hora' in e and 'evento' in e for e in eventos))

    def test_2_pid_inexistente_termina_rapido(self):
        v = self.vigia('--folga', '0.2', '--max', '30')
        self.esperar_vivo()
        t0 = time.monotonic()
        self.pedido('p.json', {'host': 'local_a', 'pid': 99999996})
        out = self.terminar(v)
        self.assertEqual(v.returncode, 0, out)
        self.assertLess(time.monotonic() - t0, 4, out)
        self.assertEqual(self.fim(out)['pid'], 99999996)

    def test_3_pedido_sem_pid_rejeitado_e_o_valido_seguinte_atendido(self):
        v = self.vigia('--folga', '0.2', '--max', '30')
        self.esperar_vivo()
        self.pedido('ruim.json', {'host': 'local_a'})
        time.sleep(1.2)
        self.pedido('bom.json', {'host': 'local_b', 'pid': 99999996})
        out = self.terminar(v)
        self.assertEqual(v.returncode, 0, out)
        self.assertEqual(self.lista('rejeitados'), ['ruim.json'])
        self.assertEqual(self.fim(out)['host'], 'local_b')

    def test_4_json_pela_metade_que_se_completa(self):
        v = self.vigia('--folga', '0.2', '--max', '30')
        self.esperar_vivo()
        p = os.path.join(self.pasta('pedidos'), 'p.json')
        with open(p, 'w', encoding='utf-8') as f:
            f.write('{"host": "local_a", "pi')
        time.sleep(1.5)
        with open(p, 'w', encoding='utf-8') as f:
            f.write('{"host": "local_a", "pid": 99999996}')
        out = self.terminar(v)
        self.assertEqual(v.returncode, 0, out)
        self.assertEqual(self.lista('rejeitados'), [])
        self.assertEqual(self.fim(out)['host'], 'local_a')

    def test_5_ja_voltou_pelo_peaks_nao_manda_segue(self):
        with open(os.path.join(self.cfg, '.context-peaks.json'), 'w', encoding='utf-8') as f:
            json.dump({'sid1': {'lineage': 'host:local_a', 'started': iso(+60)},
                       'sid2': {'lineage': 'host:local_outro', 'started': iso(+60)}}, f)
        v = self.vigia('--folga', '0.2', '--max', '5')
        self.esperar_vivo()
        self.pedido('p.json', {'host': 'local_a', 'pid': 99999996, 'hora': iso(0)})
        out = self.terminar(v)
        self.assertEqual(v.returncode, 3, out)
        self.assertNotIn(' fim ', out)
        self.assertIn('ja-voltou', out)
        self.assertEqual(self.lista('feitos'), ['p.json'])

    def test_6_segundo_vigia_com_um_vivo_sai_com_7(self):
        v1 = self.vigia('--max', '30')
        self.esperar_vivo()
        v2 = self.vigia('--max', '30')
        out = self.terminar(v2, 15)
        self.assertEqual(v2.returncode, 7, out)
        with open(os.path.join(self.estado, 'vivo.json'), encoding='utf-8') as f:
            self.assertEqual(json.load(f)['pid'], v1.pid)  # o segundo nao mexeu no vivo.json

    def test_7_cli_que_morre_da_6_e_remove_vivo(self):
        c = self.dormir(60)
        v = self.vigia('--cli', str(c.pid), '--max', '30')
        self.esperar_vivo()
        with open(os.path.join(self.estado, 'vivo.json'), encoding='utf-8') as f:
            self.assertEqual(json.load(f)['cli'], c.pid)
        c.kill()
        c.wait()
        out = self.terminar(v, 15)
        self.assertEqual(v.returncode, 6, out)
        self.sem_vivo()

    def test_8_pid_que_nao_sai_no_prazo_vai_para_rejeitados_e_o_laco_continua(self):
        s = self.dormir(60)
        v = self.vigia('--espera', '2', '--folga', '0.2', '--max', '6')
        self.esperar_vivo()
        self.pedido('preso.json', {'host': 'local_a', 'pid': s.pid})
        out = self.terminar(v)
        self.assertEqual(v.returncode, 3, out)  # continuou ate o --max
        self.assertEqual(self.lista('rejeitados'), ['preso.json'])
        self.assertIn('pid nao saiu', out)

    def test_9_pedido_preexistente_e_processado(self):
        self.pedido('velho.json', {'host': 'local_a', 'pid': 99999996})
        v = self.vigia('--folga', '0.2', '--max', '30')
        out = self.terminar(v)
        self.assertEqual(v.returncode, 0, out)
        self.assertEqual(self.fim(out)['pedido'], 'velho.json')
        self.assertEqual(self.lista('feitos'), ['velho.json'])


if __name__ == '__main__':
    unittest.main()
