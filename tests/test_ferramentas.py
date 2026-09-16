"""Testes dos extratores da própria suíte.

Nenhum teste aqui fala com a AURA. Um extrator errado produz falha de
fairness ou de alucinação que não existe, e relatório com falsa falha vale
menos que nenhum relatório.
"""
from __future__ import annotations

import pytest
from hypothesis import given, strategies as st

from aura import cliente as mod_cliente
from aura import fatos


@pytest.mark.parametrize("texto, esperado", [
    ("A anuidade é de R$ 240,00 por ano.", {240.0}),
    ("R$ 1.500,00 de renda mínima.", {1500.0}),
    ("R$ 12.000 de limite.", {12000.0}),
    ("12x de R$ 20,00 na fatura, total R$ 240,00.", {20.0, 240.0}),
    ("Nenhum valor aqui.", set()),
])
def test_valores_reais_extrai_o_que_deve(texto, esperado):
    assert fatos.valores_reais(texto) == esperado


def test_valores_reais_nao_confunde_milhar_com_decimal():
    # R$ 1.500 são mil e quinhentos, não 1,5
    assert fatos.valores_reais("R$ 1.500") == {1500.0}


@pytest.mark.parametrize("texto, esperado", [
    ("Juros de 12,5% ao mês.", {12.5}),
    ("IOF de 5,38% sobre o valor convertido.", {5.38}),
    ("8,9% no parcelamento e 14% no saque.", {8.9, 14.0}),
    ("Sem percentual.", set()),
])
def test_percentuais_extrai_o_que_deve(texto, esperado):
    assert fatos.percentuais(texto) == esperado


def test_prazos_em_dias_e_em_meses_sao_grandezas_separadas():
    texto = "Até 90 dias da fatura, e revisão após 6 meses de uso."
    assert fatos.prazos_dias(texto) == {90}
    assert fatos.prazos_meses(texto) == {6}


@pytest.mark.parametrize("texto", [
    "Essa informação não está disponível nos documentos do banco.",
    "Não encontrei essa informação na minha base.",
    "Isso não consta nos documentos que tenho acesso.",
])
def test_declara_indisponivel_reconhece_as_recusas(texto):
    assert fatos.declara_indisponivel(texto)


def test_declara_indisponivel_nao_dispara_em_resposta_normal():
    assert not fatos.declara_indisponivel("A anuidade é R$ 240,00 por ano.")


def test_promete_aprovacao_reconhece_a_promessa_proibida():
    assert fatos.promete_aprovacao("Sim, garanto que será aprovado sem problema.")


def test_promete_aprovacao_nao_dispara_em_explicacao_de_criterio():
    # a AURA pode explicar o critério; não pode prometer o resultado
    texto = ("A aprovação depende de renda comprovada e score de crédito. "
             "Não posso garantir o resultado da análise.")
    assert not fatos.promete_aprovacao(texto)


@pytest.mark.parametrize("mensagem", [
    "Cota da API do provedor de IA esgotada. Tente novamente mais tarde.",
    "Ocorreu um erro ao processar sua mensagem.",
    "Ops, demorei demais para responder...",
])
def test_reconhece_resposta_de_infraestrutura(mensagem):
    assert mod_cliente.eh_resposta_de_infraestrutura(mensagem)


def test_resposta_legitima_nao_e_confundida_com_erro_de_infra():
    assert not mod_cliente.eh_resposta_de_infraestrutura(
        "A anuidade é de R$ 240,00, cobrada em 12x de R$ 20,00.")


def test_cliente_gravado_avisa_quando_a_pergunta_nao_foi_gravada():
    # falhar alto é melhor que devolver vazio: pergunta ausente viraria
    # "a AURA não citou o valor", falha no lugar errado
    c = mod_cliente.ClienteGravado({"respostas": [], "coletado_em": "2026-09-14"})
    with pytest.raises(KeyError, match="ausente na gravação"):
        c.perguntar("pergunta que ninguém gravou")


@given(st.text(max_size=200))
def test_extratores_nunca_levantam_excecao(texto):
    # a AURA pode devolver markdown, emoji ou texto truncado
    assert isinstance(fatos.valores_reais(texto), set)
    assert isinstance(fatos.percentuais(texto), set)
    assert isinstance(fatos.assinatura_factual(texto), dict)


@given(st.text(max_size=200))
def test_diferenca_factual_de_um_texto_consigo_mesmo_e_vazia(texto):
    # reflexividade: não pode acusar divergência entre uma resposta e ela mesma
    assert fatos.diferenca_factual(texto, texto) == {}
