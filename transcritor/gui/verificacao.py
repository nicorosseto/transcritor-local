"""Janela "Verificar PC e preparar": o que o app precisa, o que falta, e botões para resolver."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from pathlib import Path

import customtkinter as ctk

from .. import ocr, preparacao
from ..config import PRESETS
from ..hardware import AVISO, ERRO, OK, diagnosticar
from ..util import localizar_binario, pasta_do_app
from .componentes import som_aviso, trazer_para_frente

ICONE = {OK: "✅", AVISO: "⚠️", ERRO: "❌", "info": "ℹ️"}
VERDE, LARANJA, VERMELHO, CINZA = "#2e7d32", "#c77700", "#c62828", "gray50"


@dataclass
class Situacao:
    """Resultado consolidado da verificação, usado também pelo selo do botão."""
    ffmpeg_ok: bool = True
    ffmpeg_embutido: bool = False
    modelo_baixado: bool = True
    modelo: str = ""
    tesseract_ok: bool = True
    diagnostico: object = None
    obrigatorios: list[str] = field(default_factory=list)
    opcionais: list[str] = field(default_factory=list)

    @property
    def total_pendencias(self) -> int:
        return len(self.obrigatorios) + len(self.opcionais)


def verificar(preset: str, pasta_saida: Path | None) -> Situacao:
    """Roda fora da thread da interface (pode demorar alguns segundos)."""
    s = Situacao(modelo=PRESETS[preset]["modelo"])
    ff = localizar_binario("ffmpeg")
    s.ffmpeg_ok = ff is not None
    s.ffmpeg_embutido = bool(ff and Path(ff).parent == pasta_do_app() / "bin")
    try:
        s.modelo_baixado = preparacao.estado_modelo(s.modelo).baixado
    except Exception:
        s.modelo_baixado = False
    est = ocr.verificar()
    s.tesseract_ok = est.disponivel
    s.diagnostico = diagnosticar(pasta_saida)
    if not s.ffmpeg_ok:
        s.obrigatorios.append("FFmpeg")
    if not s.modelo_baixado:
        s.obrigatorios.append("Modelo de transcrição")
    if not s.tesseract_ok:
        s.opcionais.append("Tesseract")
    return s


class JanelaVerificacao(ctk.CTkToplevel):
    def __init__(self, app, situacao: Situacao, preset: str, pasta_saida: Path | None, ao_mudar=None):
        super().__init__(app)
        self.app, self.preset, self.pasta_saida, self.ao_mudar = app, preset, pasta_saida, ao_mudar
        self.title("Verificar PC e preparar")
        self.geometry("760x640")
        self.minsize(680, 520)
        self.corpo = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.corpo.pack(fill="both", expand=True, padx=14, pady=(14, 6))
        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=14, pady=(0, 14))
        ctk.CTkButton(rodape, text="Fechar", width=120, fg_color="gray55", hover_color="gray45",
                      command=self._fechar).pack(side="right")
        self.btn_reverificar = ctk.CTkButton(rodape, text="Verificar de novo", width=150, command=self._reverificar)
        self.btn_reverificar.pack(side="right", padx=8)
        self.protocol("WM_DELETE_WINDOW", self._fechar)
        self._desenhar(situacao)
        trazer_para_frente(self, app)
        if situacao.total_pendencias:
            self.after(80, lambda: som_aviso(self))

    # ------------------------------------------------------------------ desenho
    def _limpar(self):
        for w in self.corpo.winfo_children():
            w.destroy()

    def _desenhar(self, s: Situacao):
        self._limpar()
        if s.obrigatorios:
            titulo, cor = f"⚠️ Falta {len(s.obrigatorios)} item obrigatório antes de começar", VERMELHO
        elif s.opcionais:
            titulo, cor = "✅ Pronto para transcrever (1 item opcional disponível)", LARANJA
        else:
            titulo, cor = "✅ Tudo pronto", VERDE
        ctk.CTkLabel(self.corpo, text=titulo, font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=cor, anchor="w").pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(self.corpo, anchor="w", justify="left", wraplength=680, text_color=CINZA,
                     text="O Transcritor roda 100% no seu PC. Alguns componentes são grandes demais para vir "
                          "no instalador e são baixados uma única vez, só quando você precisar deles.").pack(fill="x")

        self._secao("O que o app precisa")
        self._cartao("✅", "Motor do app (Python e bibliotecas)",
                     "Já vem dentro do app. Você NÃO precisa instalar Python.", VERDE)
        if s.ffmpeg_ok:
            self._cartao("✅", "FFmpeg (lê os vídeos)",
                         "Já vem dentro do app." if s.ffmpeg_embutido else "Encontrado no seu PC.", VERDE)
        else:
            self._cartao("❌", "FFmpeg (lê os vídeos)",
                         "Obrigatório e não encontrado. Reinstale o app (o FFmpeg vem na pasta \"bin\") ou "
                         "instale com: winget install --id Gyan.FFmpeg -e", VERMELHO)
        rot = PRESETS[self.preset]["rotulo"]
        tam = preparacao.TAMANHO_APROX.get(s.modelo, 1.6e9) / 1e9
        if s.modelo_baixado:
            self._cartao("✅", f"Modelo de transcrição ({rot}: {s.modelo})",
                         "Já baixado. Funciona sem internet.", VERDE)
        else:
            c = self._cartao("⬇️", f"Modelo de transcrição ({rot}: {s.modelo})",
                             f"Obrigatório. É o \"cérebro\" que transforma fala em texto. Precisa ser baixado "
                             f"uma vez (~{str(round(tam, 1)).replace('.', ',')} GB); depois funciona sem "
                             f"internet. Leva de 5 a 30 min, conforme a sua conexão.", LARANJA)
            self._acao_baixar(c, s.modelo)
        if s.tesseract_ok:
            self._cartao("✅", "Tesseract (lê texto que aparece na tela)", "Instalado.", VERDE)
        else:
            c = self._cartao("ℹ️", "Tesseract (opcional)",
                             "Só é necessário para a opção \"Ler texto da tela\" (slides, código, menus). "
                             "Sem ele, a transcrição da fala funciona normalmente. Instalação: ~50 MB.", CINZA)
            ctk.CTkButton(c, text="Instalar Tesseract", width=160, command=self._instalar_tesseract
                          ).pack(anchor="w", padx=(46, 0), pady=(4, 2))

        self._secao("Seu computador")
        d = s.diagnostico
        for i in d.itens:
            if i.nome.startswith(("FFmpeg", "Tesseract")):
                continue
            cor = {OK: VERDE, AVISO: LARANJA, ERRO: VERMELHO}.get(i.nivel, CINZA)
            self._cartao(ICONE.get(i.nivel, ""), f"{i.nome}: {i.valor}", i.explicacao, cor)
        ctk.CTkLabel(self.corpo, anchor="w", text_color=CINZA,
                     text=f"Recomendação para este PC: qualidade \"{PRESETS[d.preset_recomendado]['rotulo']}\", "
                          f"rodando em {d.dispositivo.upper()}.").pack(fill="x", pady=(10, 0))

    def _secao(self, texto):
        ctk.CTkLabel(self.corpo, text=texto, font=ctk.CTkFont(size=14, weight="bold"),
                     anchor="w").pack(fill="x", pady=(16, 4))

    def _cartao(self, icone, titulo, texto, cor):
        c = ctk.CTkFrame(self.corpo)
        c.pack(fill="x", pady=3)
        linha = ctk.CTkFrame(c, fg_color="transparent")
        linha.pack(fill="x", padx=10, pady=(8, 0))
        ctk.CTkLabel(linha, text=icone, width=28, font=ctk.CTkFont(size=16)).pack(side="left")
        ctk.CTkLabel(linha, text=titulo, anchor="w", text_color=cor,
                     font=ctk.CTkFont(weight="bold")).pack(side="left", padx=8)
        ctk.CTkLabel(c, text=texto, anchor="w", justify="left", wraplength=620).pack(
            fill="x", padx=(46, 10), pady=(2, 8))
        return c

    # ------------------------------------------------------------------ ações
    def _acao_baixar(self, cartao, modelo):
        linha = ctk.CTkFrame(cartao, fg_color="transparent")
        linha.pack(fill="x", padx=(46, 10), pady=(0, 10))
        btn = ctk.CTkButton(linha, text="Baixar agora", width=140)
        btn.pack(side="left")
        barra = ctk.CTkProgressBar(linha, width=300)
        rotulo = ctk.CTkLabel(linha, text="")

        def iniciar():
            btn.configure(state="disabled", text="Baixando...")
            barra.set(0)
            barra.pack(side="left", padx=10)
            rotulo.pack(side="left")
            self.app.baixar_modelo(modelo, lambda f, t: self.after(0, lambda: atualizar(f, t)), concluido)

        def atualizar(f, t):
            if barra.winfo_exists():
                barra.set(f / t if t else 0)
                rotulo.configure(text=f"{f / 1e6:,.0f} de ~{t / 1e6:,.0f} MB".replace(",", "."))

        def concluido(erro):
            if not self.winfo_exists():
                return
            if erro:
                btn.configure(state="normal", text="Tentar de novo")
                rotulo.configure(text=f"Falhou: {erro}", text_color=VERMELHO)
            else:
                self._reverificar()
        btn.configure(command=iniciar)

    def _instalar_tesseract(self):
        msg = preparacao.instalar_tesseract()
        ctk.CTkLabel(self.corpo, text="ℹ️ " + msg, wraplength=660, justify="left",
                     text_color=LARANJA).pack(fill="x", pady=(8, 0))

    def _reverificar(self):
        self.btn_reverificar.configure(state="disabled", text="Verificando...")

        def tarefa():
            s = verificar(self.preset, self.pasta_saida)
            self.after(0, lambda: self._depois(s))
        threading.Thread(target=tarefa, daemon=True).start()

    def _depois(self, s):
        if not self.winfo_exists():
            return
        self.btn_reverificar.configure(state="normal", text="Verificar de novo")
        self._desenhar(s)
        if self.ao_mudar:
            self.ao_mudar(s)

    def _fechar(self):
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()
