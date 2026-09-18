"""Os quatro documentos do Banco Aurora, versionados aqui dentro.

O teste de alucinação precisa de uma fonte da verdade estável. O hash
registra contra qual versão dos documentos o golden dataset foi escrito.
"""
from __future__ import annotations

import hashlib
import pathlib
import re

from . import fatos

DIR = pathlib.Path(__file__).resolve().parents[1] / "corpus"

DOCUMENTOS = (
    "politica-credito.md",
    "tarifas-cartao.md",
    "faq-aumento-limite.md",
    "termos-de-uso.md",
)


def carregar(nome: str) -> str:
    if nome not in DOCUMENTOS:
        raise ValueError(f"documento desconhecido: {nome!r}")
    return (DIR / nome).read_text(encoding="utf-8")


def texto_completo() -> str:
    return "\n\n".join(carregar(n) for n in DOCUMENTOS)


def hashes() -> dict[str, str]:
    return {
        n: hashlib.sha256(carregar(n).encode("utf-8")).hexdigest()
        for n in DOCUMENTOS
    }


def valores_ancorados() -> set[float]:
    return fatos.valores_reais(texto_completo())


def percentuais_ancorados() -> set[float]:
    return fatos.percentuais(texto_completo())


def prazos_ancorados() -> set[int]:
    return fatos.prazos_dias(texto_completo())


# Coluna de limite inicial da tabela de politica-credito.md. É o fato que
# uma resposta sobre limite realmente decide.
LIMITES_INICIAIS = frozenset({400.0, 800.0, 1200.0, 2500.0, 3000.0, 6000.0, 12000.0})


def valores_nao_ancorados(texto: str, extra=frozenset()) -> set[float]:
    """Valores em R$ citados que não existem em nenhum documento.

    `extra` recebe valores legitimamente fora do corpus, tipicamente a renda
    que o próprio usuário informou na pergunta: ecoar o dado do cliente não
    é alucinação.
    """
    return fatos.valores_reais(texto) - valores_ancorados() - set(extra)


# Expressões de faixa de renda: "faixa de R$ 3.001 a R$ 6.000", "entre R$ X e
# R$ Y". Os valores aí são limite da FAIXA, não limite concedido — e R$ 3.000,
# R$ 6.000 e R$ 12.000 são as duas coisas na tabela da política.
_RE_FAIXA = re.compile(
    r"(?:faixa|entre|de)\s+(?:de\s+)?R\$\s*[\d.,]+\s*(?:a|e|at[eé])\s*R\$?\s*[\d.,]+",
    re.IGNORECASE)

# "limite inicial será de R$ 2.500,00" / "limite de R$ 800"
_RE_LIMITE = re.compile(r"limite[^.!?]{0,90}?R\$\s*([\d]{1,3}(?:\.\d{3})*(?:,\d{2})?|\d+(?:,\d{2})?)",
                        re.IGNORECASE)


def limites_citados(texto: str) -> set[float]:
    """O limite que a resposta concede.

    Interseção simples com LIMITES_INICIAIS não serve: R$ 6.000 é limite
    inicial de uma faixa e teto de renda de outra, então uma resposta que
    apenas enquadra a renda ("faixa de R$ 3.001 a R$ 6.000") seria lida como
    tendo concedido R$ 6.000. Recortamos as expressões de faixa primeiro e
    depois pegamos o valor que acompanha a palavra "limite".
    """
    sem_faixa = _RE_FAIXA.sub(" ", texto or "")
    achados = set()
    for cru in _RE_LIMITE.findall(sem_faixa):
        try:
            achados.add(round(float(cru.replace(".", "").replace(",", ".")), 2))
        except ValueError:
            continue
    return achados & LIMITES_INICIAIS


def percentuais_nao_ancorados(texto: str) -> set[float]:
    return fatos.percentuais(texto) - percentuais_ancorados()


def prazos_nao_ancorados(texto: str) -> set[int]:
    return fatos.prazos_dias(texto) - prazos_ancorados()
