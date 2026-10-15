"""Funções utilitárias: formatação de tempo, localização de binários e execução de processos."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

# No Windows, impede que cada chamada ao ffmpeg/tesseract abra uma janela preta de console
_SEM_JANELA = 0x08000000 if sys.platform == "win32" else 0


def hhmmss(segundos: float) -> str:
    s = max(0, int(segundos))
    return f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}"


def pasta_do_app() -> Path:
    """Pasta onde o programa está (funciona tanto no código-fonte quanto no .exe do PyInstaller)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def pasta_dados_usuario() -> Path:
    """Pasta gravável por usuário (ex.: C:/Users/fulano/AppData/Local/TranscritorLocal)."""
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    destino = base / "TranscritorLocal"
    destino.mkdir(parents=True, exist_ok=True)
    return destino


def localizar_binario(nome: str, extras: list[Path] | None = None) -> str | None:
    """Procura um executável: primeiro ao lado do app (versão empacotada), depois no PATH."""
    exe = f"{nome}.exe" if sys.platform == "win32" else nome
    candidatos = [pasta_do_app() / "bin" / exe, pasta_do_app() / exe]
    candidatos += [Path(p) / exe for p in (extras or [])]
    for c in candidatos:
        if c.is_file():
            return str(c)
    return shutil.which(nome)


def rodar(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    """subprocess.run sem janela de console no Windows e sem herdar o teclado
    (sem isso, ffmpeg/ffprobe "comem" o que o usuário digita no terminal)."""
    kwargs.setdefault("stdin", subprocess.DEVNULL)
    if _SEM_JANELA:
        kwargs.setdefault("creationflags", _SEM_JANELA)
    return subprocess.run(cmd, **kwargs)


def popen(cmd: list[str], **kwargs) -> subprocess.Popen:
    kwargs.setdefault("stdin", subprocess.DEVNULL)
    if _SEM_JANELA:
        kwargs.setdefault("creationflags", _SEM_JANELA)
    return subprocess.Popen(cmd, **kwargs)


def numero_br(valor: float, casas: int = 2) -> str:
    """1.48 -> '1,48' (para o CSV abrir certo no Excel em português)."""
    return f"{valor:.{casas}f}".replace(".", ",")


def ler_numero_br(texto: str | None) -> float:
    if not texto:
        return 0.0
    try:
        return float(str(texto).replace(",", "."))
    except ValueError:
        return 0.0


def garantir_saidas_padrao() -> None:
    """No .exe de janela (sem console), sys.stdout/stderr são None e qualquer print ou barra
    de progresso (ex.: download do modelo) derruba o app. Redireciona para um arquivo de log."""
    if sys.stdout is not None and sys.stderr is not None:
        return
    log = open(pasta_dados_usuario() / "transcritor.log", "a", encoding="utf-8", buffering=1)
    if sys.stdout is None:
        sys.stdout = log
    if sys.stderr is None:
        sys.stderr = log


def nome_temporario(destino: Path, sufixo: str = ".tmp") -> Path:
    """Nome temporário ÚNICO ao lado do destino (achado N20).

    Nunca reaproveitar o mesmo nome (ex.: registro.tmp): no Windows Sandbox, e em PCs com
    alguns filtros de arquivo (sincronização, segurança), criar de novo um arquivo com o nome de
    um que acabou de ser renomeado falha com "No such file or directory"."""
    return destino.with_name(f"{destino.name}.{uuid.uuid4().hex[:8]}{sufixo}")


def _apagar(caminho: Path) -> None:
    try:
        caminho.unlink(missing_ok=True)
    except OSError:
        pass


def gravar_atomico(destino: Path, escrever, tentativas: int = 5, espera: float = 1.0) -> None:
    """Grava via arquivo temporário único e troca de uma vez (um corte no meio não deixa o arquivo
    pela metade). escrever(caminho) grava o conteúdo nesse caminho.

    Qualquer erro de disco (arquivo travado pelo Excel, antivírus examinando, filtro do sistema)
    ganha novas tentativas com um nome novo. Se todas falharem, levanta o último erro."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    ultimo: OSError | None = None
    for n in range(tentativas):
        tmp = nome_temporario(destino)
        try:
            escrever(tmp)
            os.replace(tmp, destino)
            return
        except OSError as e:
            ultimo = e
            _apagar(tmp)
            if n < tentativas - 1:
                time.sleep(espera)
        except BaseException:  # outro erro (codificação, Ctrl+C): não deixa o temporário para trás (K13)
            _apagar(tmp)
            raise
    assert ultimo is not None
    raise ultimo


def gravar_texto_atomico(destino: Path, texto: str, encoding: str = "utf-8") -> None:
    gravar_atomico(destino, lambda p: p.write_text(texto, encoding=encoding))


class ManterAcordado:
    """Impede o Windows de suspender o PC enquanto um lote roda (não impede desligar a tela)."""
    _CONTINUOUS, _SYSTEM_REQUIRED = 0x80000000, 0x00000001

    def __enter__(self):
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.kernel32.SetThreadExecutionState(self._CONTINUOUS | self._SYSTEM_REQUIRED)
            except Exception:
                pass
        return self

    def __exit__(self, *exc):
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.kernel32.SetThreadExecutionState(self._CONTINUOUS)
            except Exception:
                pass
        return False


class Cancelado(Exception):
    """O usuário pediu para cancelar agora."""


class PastaEmUso(RuntimeError):
    pass


class Trava:
    """Arquivo-trava na pasta de saída: só um fluxo por vez lê ou grava o projeto (achado X4).

    - Criação atômica (O_CREAT | O_EXCL): duas tentativas simultâneas não entram as duas.
    - Não é reentrante: o mesmo processo não entra duas vezes na mesma pasta.
    - Trava "abandonada" (processo que morreu) é retomada.
    - Só apaga a trava se ela ainda for sua (conteúdo = PID + identificador único).
    """

    _ativas: set[str] = set()
    _lock = threading.Lock()
    MENSAGEM = ("Esta pasta de saída já está sendo usada (outra janela do Transcritor ou uma leitura/rodada "
                "em andamento). Aguarde terminar, feche a outra janela ou escolha outra pasta de saída.")

    def __init__(self, pasta: Path):
        self.arquivo = pasta / ".em_uso.lock"
        self._chave = os.path.normcase(str(self.arquivo.absolute()))
        self._marca = f"{os.getpid()} {uuid.uuid4().hex}"

    def _criar(self) -> bool:
        try:
            fd = os.open(self.arquivo, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return False
        with os.fdopen(fd, "w") as f:
            f.write(self._marca)
        return True

    def __enter__(self):
        self.arquivo.parent.mkdir(parents=True, exist_ok=True)
        with Trava._lock:
            if self._chave in Trava._ativas:
                raise PastaEmUso(self.MENSAGEM)
            if not self._criar():
                try:
                    pid = int((self.arquivo.read_text().split() or ["0"])[0])
                except (ValueError, OSError):
                    pid = 0
                if pid and pid != os.getpid() and _pid_vivo(pid):
                    raise PastaEmUso(self.MENSAGEM)
                # abandonada: processo morto, ou deste processo sem nenhum contexto ativo
                try:
                    self.arquivo.unlink()
                except FileNotFoundError:
                    pass
                if not self._criar():
                    raise PastaEmUso(self.MENSAGEM)
            Trava._ativas.add(self._chave)
        return self

    def __exit__(self, *exc):
        with Trava._lock:
            Trava._ativas.discard(self._chave)
            try:
                if self.arquivo.read_text() == self._marca:
                    self.arquivo.unlink()
            except OSError:
                pass
        return False


def _pid_vivo(pid: int) -> bool:
    try:
        import psutil
        return psutil.pid_exists(pid)
    except ImportError:
        return True
