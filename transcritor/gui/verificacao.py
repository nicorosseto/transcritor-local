"""Página "Preparação do PC": o que o app precisa, o que falta, e botões para resolver."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import customtkinter as ctk

from .. import ocr, preparacao
from ..config import PRESETS
from ..hardware import AVISO, ERRO, OK, diagnosticar
from ..util import localizar_binario, pasta_do_app
from . import tema
from .tema import CINZA, LARANJA, VERDE, VERMELHO

ICONE = {OK: "✓", AVISO: "!", ERRO: "✕", "info": "i"}


@dataclass
class Situacao:
    """Resultado consolidado da verificação, usado também pelo selo do botão."""
    ffmpeg_ok: bool = True
    ffmpeg_embutido: bool = False
    modelo_baixado: bool = True
    modelo: str = ""
    tesseract_ok: bool = True
    tesseract_portugues: bool = True
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
    s.tesseract_portugues = est.tem_portugues
    s.diagnostico = diagnosticar(pasta_saida)
    if not s.ffmpeg_ok:
        s.obrigatorios.append("FFmpeg")
    if not s.modelo_baixado:
        s.obrigatorios.append("Modelo de transcrição")
    if not s.tesseract_ok:
        s.opcionais.append("Tesseract")
    return s


class PainelVerificacao(ctk.CTkFrame):
    """Página da janela principal (antes era uma janela por cima; layout aprovado em 11/10/2026)."""

    def __init__(self, pai, app):
        super().__init__(pai, fg_color="transparent")
        self.app = app
        self.preset, self.pasta_saida = "equilibrado", None
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        ctk.CTkLabel(self, text="Preparação do PC", font=ctk.CTkFont(size=22, weight="bold"),
                     anchor="w").grid(row=0, column=0, sticky="w")
        self.btn_reverificar = ctk.CTkButton(self, text="Verificar de novo", width=150,
                                             command=self._reverificar, **tema.secundario())
        self.btn_reverificar.grid(row=0, column=1, sticky="e")
        self.lbl_sub = ctk.CTkLabel(self, text="Verificando o PC...", anchor="w", text_color=CINZA)
        self.lbl_sub.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(2, 10))
        self.corpo = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.corpo.grid(row=2, column=0, columnspan=2, sticky="nsew")

    def verificando(self) -> None:
        """Enquanto a verificação roda de novo, não deixa à mostra um cartão que já não vale (N18)."""
        self._limpar()
        self.lbl_sub.configure(text="Verificando o PC para a qualidade escolhida...", text_color=CINZA)

    def mostrar(self, situacao: Situacao, preset: str, pasta_saida: Path | None) -> None:
        self.preset, self.pasta_saida = preset, pasta_saida
        self.btn_reverificar.configure(state="normal", text="Verificar de novo")
        self._desenhar(situacao)

    # ------------------------------------------------------------------ desenho
    def _limpar(self):
        for w in self.corpo.winfo_children():
            w.destroy()

    def _desenhar(self, s: Situacao):
        self._limpar()
        if s.obrigatorios:
            n = len(s.obrigatorios)
            titulo, cor = f"Falta {n} item obrigatório antes de começar." if n == 1 else \
                f"Faltam {n} itens obrigatórios antes de começar.", VERMELHO
        elif s.opcionais:
            titulo, cor = "Pronto para transcrever. Há 1 item opcional.", CINZA
        else:
            titulo, cor = "Tudo pronto.", VERDE
        self.lbl_sub.configure(text=titulo + " Componentes grandes são baixados uma vez, só quando precisar.",
                               text_color=cor)

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
            self._acao_baixar(c, s.modelo, tam)
        if s.tesseract_ok:
            self._cartao("✅", "Tesseract (lê texto que aparece na tela)", "Instalado.", VERDE)
        else:
            c = self._cartao("ℹ️", "Tesseract (opcional)",
                             "Só é necessário para a opção \"Ler texto da tela\" (slides, código, menus). "
                             "Sem ele, a transcrição da fala funciona normalmente. Instalação: ~50 MB.", CINZA)
            ctk.CTkButton(c, text="Instalar Tesseract", width=160, command=self._instalar_tesseract,
                          **tema.secundario()).pack(anchor="w", padx=(46, 0), pady=(4, 10))

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
        ctk.CTkLabel(self.corpo, text=texto.upper(), font=ctk.CTkFont(size=11), text_color=CINZA,
                     anchor="w").pack(fill="x", pady=(16, 4))

    def _cartao(self, icone, titulo, texto, cor):
        destaque = cor in (VERMELHO, LARANJA)
        c = ctk.CTkFrame(self.corpo, border_width=1, corner_radius=10,
                         border_color=cor if destaque else tema.BORDA)
        c.pack(fill="x", pady=4)
        linha = ctk.CTkFrame(c, fg_color="transparent")
        linha.pack(fill="x", padx=10, pady=(8, 0))
        ctk.CTkLabel(linha, text=icone, width=28, font=ctk.CTkFont(size=16)).pack(side="left")
        ctk.CTkLabel(linha, text=titulo, anchor="w", text_color=cor,
                     font=ctk.CTkFont(weight="bold")).pack(side="left", padx=8)
        ctk.CTkLabel(c, text=texto, anchor="w", justify="left", wraplength=620).pack(
            fill="x", padx=(46, 10), pady=(2, 8))
        return c

    # ------------------------------------------------------------------ ações
    def _acao_baixar(self, cartao, modelo, tamanho_gb: float):
        linha = ctk.CTkFrame(cartao, fg_color="transparent")
        linha.pack(fill="x", padx=(46, 10), pady=(0, 10))
        tam = str(round(tamanho_gb, 1)).replace(".", ",")
        btn = ctk.CTkButton(linha, text=f"Baixar {modelo} (~{tam} GB)", width=200,
                            font=ctk.CTkFont(weight="bold"))
        btn.pack(side="left")
        barra = ctk.CTkProgressBar(linha, width=300)
        rotulo = ctk.CTkLabel(linha, text="")

        def iniciar():
            btn.configure(state="disabled", text="Baixando...")
            barra.set(0)
            barra.pack(side="left", padx=10)
            rotulo.pack(side="left")
            self.app.baixar_modelo(modelo, lambda f, t: self.app.na_interface(lambda: atualizar(f, t)), concluido)

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
        """Pede a verificação ao app, que é o único que decide qual resultado vale (achado C1).
        Antes o painel verificava por conta própria e desenhava um resultado que podia estar velho."""
        self.btn_reverificar.configure(state="disabled", text="Verificando...")
        self.verificando()
        self.app._rodar_verificacao()
