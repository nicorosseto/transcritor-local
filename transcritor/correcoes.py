"""Lista de correções por projeto (correcoes.json na pasta de saída).

Diferente do vocabulário de dicas (que ajuda o Whisper a OUVIR certo), as correções TROCAM
o texto depois da transcrição: regra "Chatepte" -> "ChatGPT". São aplicadas só a palavras
inteiras, sem diferenciar maiúsculas, e o total aplicado vai para o cabeçalho do .md.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

NOME_ARQUIVO = "correcoes.json"

MODELO = {
    "_como_usar": [
        "Cada linha em 'trocar' é: \"como saiu errado\": \"como deveria ser\".",
        "Vale só para palavras inteiras e não diferencia maiúsculas de minúsculas.",
        "Cuidado com palavras que existem de verdade: 'Hulk' -> 'hook' também trocaria o Hulk dos quadrinhos.",
        "Depois de editar, salve o arquivo. Vale para as PRÓXIMAS transcrições.",
    ],
    "trocar": {
        "Chatepte": "ChatGPT",
        "Chatipete": "ChatGPT",
        "chat EPT": "ChatGPT",
        "Cloddy": "Claude",
        "Cloude": "Claude",
        "Clode": "Claude",
        "Jimenae": "Gemini",
        "Dolby Premier": "Adobe Premiere",
    },
}


def caminho(pasta_saida: Path) -> Path:
    return pasta_saida / NOME_ARQUIVO


def criar_modelo_se_faltar(pasta_saida: Path) -> Path:
    arq = caminho(pasta_saida)
    if not arq.exists():
        pasta_saida.mkdir(parents=True, exist_ok=True)
        arq.write_text(json.dumps(MODELO, ensure_ascii=False, indent=2), encoding="utf-8")
    return arq


def carregar(pasta_saida: Path) -> tuple[dict[str, str], str]:
    """Retorna (regras, aviso). Arquivo inválido não derruba nada: volta vazio com aviso."""
    arq = caminho(pasta_saida)
    if not arq.is_file():
        return {}, ""
    try:
        dados = json.loads(arq.read_text(encoding="utf-8-sig"))
        regras = dados.get("trocar", {}) if isinstance(dados, dict) else {}
        regras = {str(k).strip(): str(v) for k, v in regras.items() if str(k).strip()}
        return regras, ""
    except (json.JSONDecodeError, OSError, AttributeError) as e:
        return {}, f"O arquivo {NOME_ARQUIVO} tem um erro de formato e foi ignorado ({e})."


def compilar(regras: dict[str, str]):
    if not regras:
        return None
    # mais longas primeiro: "chat EPT" antes de "EPT"
    chaves = sorted(regras, key=len, reverse=True)
    padrao = re.compile(r"(?<!\w)(" + "|".join(re.escape(k) for k in chaves) + r")(?!\w)", re.IGNORECASE)
    minusculas = {k.lower(): v for k, v in regras.items()}
    return padrao, minusculas


def aplicar(texto: str, compilado) -> tuple[str, int]:
    if not compilado:
        return texto, 0
    padrao, mapa = compilado
    contagem = 0

    def troca(m):
        nonlocal contagem
        contagem += 1
        return mapa[m.group(1).lower()]
    return padrao.sub(troca, texto), contagem
