"""Os quatro documentos do Banco Aurora, versionados aqui dentro.

O teste de alucinação precisa de uma fonte da verdade estável. O hash
registra contra qual versão dos documentos o golden dataset foi escrito.
"""
from __future__ import annotations

import hashlib
import pathlib

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


def valores_nao_ancorados(texto: str) -> set[float]:
    """Valores em R$ citados que não existem em nenhum documento."""
    return fatos.valores_reais(texto) - valores_ancorados()


def percentuais_nao_ancorados(texto: str) -> set[float]:
    return fatos.percentuais(texto) - percentuais_ancorados()


def prazos_nao_ancorados(texto: str) -> set[int]:
    return fatos.prazos_dias(texto) - prazos_ancorados()
