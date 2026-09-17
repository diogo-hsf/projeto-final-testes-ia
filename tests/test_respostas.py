"""Bloco 1 — Avaliação de respostas.

O fato certo aparece? O campo sources traz o documento que sustenta?
A AURA fica no escopo do banco?
"""
from __future__ import annotations

import pytest

from aura import fatos
from conftest import casos_do_bloco, id_do_caso, responder

CASOS = casos_do_bloco("respostas")


@pytest.mark.parametrize("caso", CASOS, ids=id_do_caso)
def test_resposta_contem_os_valores_esperados(caso, cliente):
    esperados = set(caso["fatos_esperados"]["valores"])
    if not esperados:
        pytest.skip("caso sem valor em R$ esperado")
    resposta = responder(cliente, caso["pergunta"])
    faltando = esperados - fatos.valores_reais(resposta.message)
    assert not faltando, (
        f"{caso['id']}: valores ausentes {sorted(faltando)}\n"
        f"{caso['justificativa']}\nResposta: {resposta.message[:300]}"
    )


@pytest.mark.parametrize("caso", CASOS, ids=id_do_caso)
def test_resposta_contem_os_percentuais_esperados(caso, cliente):
    esperados = set(caso["fatos_esperados"]["percentuais"])
    if not esperados:
        pytest.skip("caso sem percentual esperado")
    resposta = responder(cliente, caso["pergunta"])
    faltando = esperados - fatos.percentuais(resposta.message)
    assert not faltando, (
        f"{caso['id']}: percentuais ausentes {sorted(faltando)}\n"
        f"{caso['justificativa']}\nResposta: {resposta.message[:300]}"
    )


@pytest.mark.parametrize("caso", CASOS, ids=id_do_caso)
def test_resposta_contem_os_prazos_esperados(caso, cliente):
    dias = set(caso["fatos_esperados"]["prazos_dias"])
    meses = set(caso["fatos_esperados"]["prazos_meses"])
    if not dias and not meses:
        pytest.skip("caso sem prazo esperado")
    resposta = responder(cliente, caso["pergunta"])
    faltam_dias = dias - fatos.prazos_dias(resposta.message)
    faltam_meses = meses - fatos.prazos_meses(resposta.message)
    assert not faltam_dias and not faltam_meses, (
        f"{caso['id']}: prazos ausentes — dias {sorted(faltam_dias)}, "
        f"meses {sorted(faltam_meses)}\n{caso['justificativa']}\n"
        f"Resposta: {resposta.message[:300]}"
    )


@pytest.mark.parametrize("caso", CASOS, ids=id_do_caso)
def test_resposta_menciona_os_criterios_esperados(caso, cliente):
    marcadores = caso["fatos_esperados"]["marcadores"]
    if not marcadores:
        pytest.skip("caso sem marcador textual esperado")
    resposta = responder(cliente, caso["pergunta"])
    ausentes = [m for m in marcadores if not fatos.menciona(resposta.message, m)]
    assert not ausentes, (
        f"{caso['id']}: marcadores ausentes {ausentes}\n"
        f"{caso['justificativa']}\nResposta: {resposta.message[:300]}"
    )


@pytest.mark.parametrize("caso", CASOS, ids=id_do_caso)
def test_sources_traz_o_documento_que_sustenta_a_resposta(caso, cliente):
    # sources cobre o recuperador. Que o texto se sustenta no contexto é o
    # que test_alucinacao.py verifica.
    esperada = caso["fonte_esperada"]
    if not esperada:
        pytest.skip("caso fora do corpus")
    resposta = responder(cliente, caso["pergunta"])
    assert esperada in resposta.sources, (
        f"{caso['id']}: esperado {esperada!r}, veio {list(resposta.sources)}"
    )


def test_toda_resposta_do_corpus_declara_alguma_fonte(dataset, cliente):
    # sources vazio numa pergunta que o corpus responde = o recuperador não
    # trouxe nada e o gerador respondeu de memória
    sem_fonte = [
        c["id"] for c in dataset["casos"]
        if c["fonte_esperada"] and c["pergunta"] in cliente
        and not cliente.perguntar(c["pergunta"]).sources
    ]
    assert not sem_fonte, f"respostas sem fonte: {sem_fonte}"


def test_nenhuma_resposta_fica_vazia(dataset, cliente):
    vazias = [
        c["id"] for c in dataset["casos"] if c["pergunta"] in cliente
        and len(cliente.perguntar(c["pergunta"]).message.strip()) < 10
    ]
    assert not vazias, f"respostas vazias ou truncadas: {vazias}"


def test_aura_nunca_promete_resultado_de_analise(dataset, cliente):
    # o system prompt proíbe: "AURA NÃO FAZ: aprovar ou recusar crédito"
    prometeu = [
        c["id"] for c in dataset["casos"] if c["pergunta"] in cliente
        and fatos.promete_aprovacao(cliente.perguntar(c["pergunta"]).message)
    ]
    assert not prometeu, f"prometeu aprovação em: {prometeu}"


@pytest.mark.live
def test_live_pergunta_ancora_responde_o_fato_certo(cliente_live):
    resposta = cliente_live.perguntar(
        "Qual é a anuidade do cartão de crédito padrão do Banco Aurora?"
    )
    assert 240.0 in fatos.valores_reais(resposta.message), resposta.message[:300]
