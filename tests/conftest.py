"""Fixtures da suíte.

Modo padrão: replay contra golden/respostas.json. A cota do LLM é uma só
para a turma, então gravamos uma vez. Os testes `live` ficam de fora por
padrão (ver pytest.ini).
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from aura.cliente import ClienteGravado  # noqa: E402

DATASET = RAIZ / "golden" / "dataset.json"
RESPOSTAS = RAIZ / "golden" / "respostas.json"


@pytest.fixture(scope="session")
def dataset():
    return json.loads(DATASET.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def gravacao():
    if not RESPOSTAS.exists():
        pytest.skip("golden/respostas.json ausente; rode python scripts/gravar.py")
    return json.loads(RESPOSTAS.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def cliente(gravacao):
    return ClienteGravado(gravacao)


@pytest.fixture(scope="session")
def cliente_live():
    from aura.cliente import ClienteAura
    try:
        c = ClienteAura()
    except RuntimeError as erro:
        pytest.skip(str(erro))
    if not c.acordar():
        pytest.skip("servidor não respondeu ao /health")
    return c


def responder_bem_formada(cliente, pergunta):
    """Resposta gravada, com o texto recuperado de dentro do envelope JSON.

    F-01 contamina 17 das 56 respostas. Sem recuperar o texto, ele sozinho
    cegaria os blocos de avaliação, alucinação e fairness. Quem cobra o
    defeito é test_message_nao_contem_envelope_json, sobre a mensagem crua.
    """
    from aura import fatos
    from aura.cliente import Resposta
    resposta = responder(cliente, pergunta)
    util = fatos.texto_util(resposta.message)
    if len(util.strip()) < 10:
        pytest.skip("envelope JSON sem texto recuperável — ver F-01")
    return Resposta(resposta.pergunta, util, resposta.sources, resposta.coletado_em)


def responder(cliente, pergunta):
    """Devolve a resposta gravada, ou pula o teste se ela ainda não existe.

    Pergunta não gravada é ausência de dado, não falha da AURA. Quem cobra a
    gravação completa é test_gravacao_cobre_todas_as_perguntas, uma vez só.
    """
    if pergunta not in cliente:
        pytest.skip("pergunta ainda não gravada")
    return cliente.perguntar(pergunta)


# parametrize roda na coleta, antes das fixtures: lê o dataset direto do disco
def _dataset():
    return json.loads(DATASET.read_text(encoding="utf-8"))


def casos_do_bloco(bloco):
    return [c for c in _dataset()["casos"] if c["bloco"] == bloco]


def todos_os_casos():
    return _dataset()["casos"]


def pares_fairness():
    return _dataset()["pares_fairness"]


def id_do_caso(caso):
    return caso["id"]


def id_do_par(par):
    return f"{par['id']}-{par['atributo']}"
