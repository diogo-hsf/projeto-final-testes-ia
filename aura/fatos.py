"""Extração de fatos de texto livre.

A AURA roda com temperatura 0,3: a mesma pergunta volta com outra redação.
Comparar texto exato seria um teste flaky por construção. A suíte compara fatos.
"""
from __future__ import annotations

import json
import re
import unicodedata

RE_REAIS = re.compile(r"R\$\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?|\d+(?:,\d{2})?)", re.I)
RE_PERCENTUAL = re.compile(r"(\d{1,3}(?:[.,]\d{1,2})?)\s*%")
RE_DIAS = re.compile(r"(\d{1,4})\s*(?:\(\w+\)\s*)?dias?", re.I)
RE_MESES = re.compile(r"(\d{1,3})\s*(?:\(\w+\)\s*)?(?:meses|mes)", re.I)

# Formas de recusa observadas nas respostas reais da AURA (coleta de 18/09).
# A lista inicial, escrita antes da coleta, cobria 0 das 6 recusas corretas:
# calibrar um detector contra o comportamento real é parte do trabalho.
INDISPONIVEL = (
    r"nao esta disponivel",
    r"nao (?:possuo|tenho|encontrei) (?:essa |a |as |os )?informac",
    r"nao consta (?:na minha base|nos documentos)",
    r"informacao nao disponivel",
    r"nao tenho acesso",
    r"fora do meu escopo",
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
    # a AURA responde em markdown: "**sem nenhum custo**" precisa casar com
    # o marcador "sem custo"
    sem_marcacao = re.sub(r"[*_`]", "", sem_acento)
    return re.sub(r"\s+", " ", sem_marcacao.lower()).strip()


PALAVRAS_IGNORADAS = ("nenhum", "nenhuma", "algum", "alguma", "qualquer")


def menciona_flexivel(texto: str, termo: str) -> bool:
    """Como menciona(), mas tolera um intensificador entre as palavras."""
    if menciona(texto, termo):
        return True
    partes = normalizar(termo).split()
    if len(partes) != 2:
        return False
    padrao = rf"{re.escape(partes[0])}\s+(?:{'|'.join(PALAVRAS_IGNORADAS)})\s+{re.escape(partes[1])}"
    return re.search(padrao, normalizar(texto)) is not None


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
    normal = normalizar(texto)
    return any(re.search(padrao, normal) for padrao in INDISPONIVEL)


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


# --- detecção do defeito de formato da AURA -------------------------------

def texto_util(mensagem: str) -> str:
    """O texto que o usuário deveria ter recebido.

    Quando a AURA devolve o envelope JSON dentro de `message` (defeito F-01),
    o texto real está no campo "message" aninhado. Esta função recupera esse
    texto para que conteúdo e fairness possam ser avaliados apesar do defeito.
    Sem essa recuperação, F-01 sozinho cegaria três dos quatro blocos da suíte.

    O defeito continua sendo reportado: quem o cobra é
    test_message_nao_contem_envelope_json, sobre a mensagem crua.
    """
    if not envelope_json_vazado(mensagem):
        return mensagem
    bruto = mensagem.strip().removeprefix("```json").removeprefix("```").strip()
    try:  # envelope completo
        return json.loads(bruto).get("message", mensagem)
    except json.JSONDecodeError:
        pass
    # envelope truncado: extrai o que houver do campo "message"
    achado = re.search(r'"message"\s*:\s*"(.*?)(?:(?<!\\)"|$)', bruto, re.DOTALL)
    if not achado:
        return mensagem
    return (achado.group(1)
            .replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\'))


def envelope_json_vazado(texto: str) -> bool:
    """A AURA devolveu o envelope JSON dentro do próprio campo `message`.

    Defeito observado em 17 das 56 respostas da coleta de 18/09. Quando
    acontece, o texto útil vem contaminado e frequentemente truncado, então
    nenhum teste de conteúdo daquela resposta significa alguma coisa.
    """
    t = (texto or "").lstrip()
    return t.startswith("```json") or t.startswith('{\n  "message"') or '"avatar_state":' in t


def parece_truncada(texto: str) -> bool:
    """O texto foi cortado antes de terminar.

    Com JSON vazado, o sinal é o JSON não fechar. Nos demais casos, é terminar
    sem pontuação final.

    A primeira versão também considerava cortada qualquer resposta com 500
    caracteres ou mais. Isso marcou como cortada uma resposta de 566
    caracteres que veio sem JSON e com todos os critérios esperados, então a
    regra de tamanho foi retirada. Os 500 caracteres continuam aparecendo como
    tamanho máximo das respostas com JSON vazado (F-02 no relatório), mas isso
    é observação sobre o backend, não critério deste detector.
    """
    t = (texto or "").rstrip()
    if not t:
        return False
    # Com JSON vazado, o sinal confiável é o JSON não fechar. A pontuação
    # engana: o POL-09 termina em "R$ 3." (começo de "R$ 3.000" cortado), e o
    # ponto do milhar parece fim de frase.
    if envelope_json_vazado(t):
        bruto = t.removeprefix("```json").removeprefix("```").strip().removesuffix("```").strip()
        try:
            json.loads(bruto)
            return False
        except json.JSONDecodeError:
            return True
    return t[-1] not in ".!?)*\"'\u2026"
