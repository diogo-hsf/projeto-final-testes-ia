"""Bloco 4 — Regressão de prompts.

O golden dataset tem três partes versionadas em golden/: as perguntas, os
fatos esperados (derivados do corpus) e as respostas gravadas com data.
A suíte normal roda contra a gravação; os testes `live` detectam mudança.
"""
from __future__ import annotations

import pytest

from aura import cliente as mod_cliente
from aura import corpus, fatos
from conftest import id_do_caso, responder, todos_os_casos

TODOS = todos_os_casos()


# Integridade do golden dataset --------------------------------------------

def test_dataset_nao_tem_pergunta_duplicada(dataset):
    perguntas = [c["pergunta"] for c in dataset["casos"]]
    repetidas = {p for p in perguntas if perguntas.count(p) > 1}
    assert not repetidas, f"perguntas repetidas: {repetidas}"


def test_dataset_nao_tem_id_duplicado(dataset):
    ids = [c["id"] for c in dataset["casos"]]
    assert len(ids) == len(set(ids))


def test_todo_caso_tem_justificativa(dataset):
    sem = [c["id"] for c in dataset["casos"] if len(c.get("justificativa", "")) < 20]
    assert not sem, f"casos sem justificativa: {sem}"


def test_fatos_esperados_existem_no_corpus(dataset):
    # se um fato esperado não existe no corpus, o erro é do dataset e a suíte
    # reprovaria a AURA por acertar
    valores = corpus.valores_ancorados()
    pcts = corpus.percentuais_ancorados()
    problemas = []
    for caso in dataset["casos"]:
        for v in caso["fatos_esperados"]["valores"]:
            if v not in valores:
                problemas.append(f"{caso['id']}: valor {v} fora do corpus")
        for p in caso["fatos_esperados"]["percentuais"]:
            if p not in pcts:
                problemas.append(f"{caso['id']}: percentual {p} fora do corpus")
    assert not problemas, "\n".join(problemas)


# Integridade da gravação --------------------------------------------------

def test_gravacao_cobre_todas_as_perguntas(dataset, cliente):
    perguntas = {c["pergunta"] for c in dataset["casos"]}
    for par in dataset["pares_fairness"]:
        perguntas |= {par["a"], par["b"]}
    ausentes = sorted(p for p in perguntas if p not in cliente)
    assert not ausentes, (
        f"{len(ausentes)} pergunta(s) sem resposta gravada; rode scripts/gravar.py\n"
        f"Primeira: {ausentes[0][:80]!r}"
    )


def test_gravacao_declara_data_de_coleta(cliente):
    assert cliente.coletado_em, "golden/respostas.json sem 'coletado_em'"


def test_gravacao_nao_contem_resposta_de_infraestrutura(dataset, cliente):
    # cota esgotada volta com HTTP 200; se entrou na gravação, todo teste de
    # conteúdo daquele caso vira ruído
    contaminadas = [
        c["id"] for c in dataset["casos"] if c["pergunta"] in cliente
        and mod_cliente.eh_resposta_de_infraestrutura(
            cliente.perguntar(c["pergunta"]).message)
    ]
    assert not contaminadas, f"gravação contaminada em: {contaminadas}"


# Regressão contra o sistema no ar -----------------------------------------

@pytest.mark.live
@pytest.mark.parametrize(
    "caso", [c for c in TODOS if c["bloco"] == "respostas"][:8], ids=id_do_caso)
def test_live_fatos_nao_regrediram_desde_a_gravacao(caso, cliente, cliente_live):
    # compara fatos, nunca texto: temperatura 0,3 muda a redação e isso não
    # é regressão
    gravada = responder(cliente, caso["pergunta"]).message
    ao_vivo = cliente_live.perguntar(caso["pergunta"]).message
    diferenca = fatos.diferenca_factual(gravada, ao_vivo)
    assert not diferenca, (
        f"{caso['id']}: fatos mudaram desde {cliente.coletado_em}: {diferenca}"
    )


@pytest.mark.live
def test_live_servico_esta_no_ar(cliente_live):
    resposta = cliente_live.perguntar("Qual é a anuidade do cartão padrão?")
    assert resposta.message.strip()
    assert not mod_cliente.eh_resposta_de_infraestrutura(resposta.message)
