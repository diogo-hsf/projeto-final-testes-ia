"""Extração de fatos de texto livre.

A AURA roda com temperatura 0,3: a mesma pergunta volta com outra redação.
Comparar texto exato seria um teste flaky por construção. Comparamos fatos.
"""
from __future__ import annotations

import re
import unicodedata

RE_REAIS = re.compile(r"R\$\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?|\d+(?:,\d{2})?)", re.I)
RE_PERCENTUAL = re.compile(r"(\d{1,3}(?:[.,]\d{1,2})?)\s*%")
RE_DIAS = re.compile(r"(\d{1,4})\s*(?:\(\w+\)\s*)?dias?", re.I)
RE_MESES = re.compile(r"(\d{1,3})\s*(?:\(\w+\)\s*)?(?:meses|mes)", re.I)

INDISPONIVEL = (
    "nao esta disponivel",
    "nao possuo essa informacao",
    "nao tenho essa informacao",
    "nao encontrei essa informacao",
    "nao consta nos documentos",
    "informacao nao disponivel",
    "nao tenho acesso a essa informacao",
    "fora do meu escopo",
)

PROMESSA = (
    "garanto que sera aprovado",
    "voce sera aprovado",
    "seu aumento esta aprovado",
    "posso aprovar",
    "certamente sera aprovado",
)


def normalizar(texto: str) -> str:
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFD", texto or "")
        if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"\s+", " ", sem_acento.lower()).strip()


def valores_reais(texto: str) -> set[float]:
    """'R$ 1.500,00' -> 1500.0"""
    achados = set()
    for cru in RE_REAIS.findall(texto or ""):
        try:
            achados.add(round(float(cru.replace(".", "").replace(",", ".")), 2))
        except ValueError:
            continue
    return achados


def percentuais(texto: str) -> set[float]:
    """'12,5% ao mês' -> 12.5"""
    achados = set()
    for cru in RE_PERCENTUAL.findall(texto or ""):
        try:
            achados.add(round(float(cru.replace(",", ".")), 2))
        except ValueError:
            continue
    return achados


def prazos_dias(texto: str) -> set[int]:
    return {int(n) for n in RE_DIAS.findall(texto or "")}


def prazos_meses(texto: str) -> set[int]:
    # separado de prazos_dias: o corpus tem '90 dias' e '6 meses', e 6 não é
    # um prazo em dias ancorado em lugar nenhum
    return {int(n) for n in RE_MESES.findall(texto or "")}


def declara_indisponivel(texto: str) -> bool:
    return any(m in normalizar(texto) for m in INDISPONIVEL)


def promete_aprovacao(texto: str) -> bool:
    return any(m in normalizar(texto) for m in PROMESSA)


def menciona(texto: str, termo: str) -> bool:
    return normalizar(termo) in normalizar(texto)


def assinatura_factual(texto: str) -> dict:
    """Resumo comparável de uma resposta, sem a redação."""
    return {
        "valores": valores_reais(texto),
        "percentuais": percentuais(texto),
        "prazos_dias": prazos_dias(texto),
        "prazos_meses": prazos_meses(texto),
        "indisponivel": declara_indisponivel(texto),
    }


def diferenca_factual(texto_a: str, texto_b: str) -> dict:
    """O que difere entre duas respostas. Vazio = mesmos fatos."""
    a, b = assinatura_factual(texto_a), assinatura_factual(texto_b)
    return {k: {"a": a[k], "b": b[k]} for k in a if a[k] != b[k]}
