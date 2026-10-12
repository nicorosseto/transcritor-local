"""P17: o padrão de threads é o número de núcleos FÍSICOS (medido em 11/10/2026)."""

from __future__ import annotations

import sys
import types

from transcritor.config import Config, threads_padrao


def _psutil_falso(monkeypatch, fisicos, logicos):
    falso = types.SimpleNamespace(cpu_count=lambda logical=True: logicos if logical else fisicos)
    monkeypatch.setitem(sys.modules, "psutil", falso)


def test_padrao_usa_nucleos_fisicos(monkeypatch, tmp_path):
    _psutil_falso(monkeypatch, 6, 12)
    assert threads_padrao() == 6
    assert Config(tmp_path, tmp_path / "s").threads_efetivas == 6


def test_valor_escolhido_pelo_usuario_tem_prioridade(monkeypatch, tmp_path):
    _psutil_falso(monkeypatch, 6, 12)
    assert Config(tmp_path, tmp_path / "s", threads=4).threads_efetivas == 4


def test_sem_contagem_fisica_usa_metade_das_logicas(monkeypatch):
    _psutil_falso(monkeypatch, None, 12)
    monkeypatch.setattr("os.cpu_count", lambda: 12)
    assert threads_padrao() == 6
