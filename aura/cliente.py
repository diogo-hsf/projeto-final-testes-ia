"""Cliente HTTP da AURA."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass

import requests

BASE = "https://assistente-financeiro-testes.onrender.com"
TIMEOUT = 180          # o servidor hiberna; a primeira chamada demora
PAUSA = 3.5            # limite de 20 chamadas/min = 3,0 s, com folga
MAX_TENTATIVAS = 3

# O servidor devolve 200 mesmo quando dá erro, com a mensagem no corpo.
ERROS_DE_INFRA = (
    "cota da api",
    "cota esgotada",
    "ocorreu um erro ao processar",
    "demorei demais para responder",
)


class RespostaDeInfraestrutura(RuntimeError):
    """Corpo 200 que é erro de infra, não resposta da AURA."""


@dataclass(frozen=True)
class Resposta:
    pergunta: str
    message: str
    sources: tuple[str, ...]
    coletado_em: str = ""

    @classmethod
    def de_dict(cls, pergunta, dados, coletado_em=""):
        return cls(
            pergunta=pergunta,
            message=dados.get("message", ""),
            sources=tuple(dados.get("sources") or ()),
            coletado_em=coletado_em,
        )

    def para_dict(self):
        return {
            "pergunta": self.pergunta,
            "message": self.message,
            "sources": list(self.sources),
            "coletado_em": self.coletado_em,
        }


def eh_resposta_de_infraestrutura(texto: str) -> bool:
    baixo = (texto or "").lower()
    return any(erro in baixo for erro in ERROS_DE_INFRA)


class ClienteAura:
    """Fala com o sistema no ar. Só usado pelos testes marcados `live`."""

    def __init__(self, usuario=None, senha=None, base=BASE):
        self.base = base.rstrip("/")
        self._usuario = usuario or os.environ.get("AURA_USUARIO", "")
        self._senha = senha or os.environ.get("AURA_SENHA", "")
        if not self._usuario or not self._senha:
            raise RuntimeError("defina AURA_USUARIO e AURA_SENHA no ambiente")
        self._token = None
        self._token_em = 0.0
        self._ultima = 0.0

    def acordar(self, tentativas=3) -> bool:
        for _ in range(tentativas):
            try:
                r = requests.get(f"{self.base}/health", timeout=TIMEOUT)
                if r.ok and r.json().get("status") == "ok":
                    return True
            except requests.RequestException:
                pass
            time.sleep(5)
        return False

    def _autenticar(self):
        # o token expira em 30 min; renova aos 25
        if self._token is None or (time.monotonic() - self._token_em) > 1500:
            r = requests.post(
                f"{self.base}/auth/login",
                json={"username": self._usuario, "password": self._senha},
                timeout=TIMEOUT,
            )
            r.raise_for_status()
            self._token = r.json()["access_token"]
            self._token_em = time.monotonic()
        return self._token

    def perguntar(self, pergunta: str) -> Resposta:
        for _ in range(MAX_TENTATIVAS):
            decorrido = time.monotonic() - self._ultima
            if decorrido < PAUSA:
                time.sleep(PAUSA - decorrido)
            self._ultima = time.monotonic()

            r = requests.post(
                f"{self.base}/chat",
                json={"message": pergunta, "history": []},
                headers={"Authorization": f"Bearer {self._autenticar()}"},
                stream=True,
                timeout=TIMEOUT,
            )
            if r.status_code == 429:
                time.sleep(int(r.headers.get("Retry-After", "60")) + 1)
                continue
            if r.status_code == 403:
                self._token = None
                continue
            r.raise_for_status()

            dados = self._ler_sse(r)
            if eh_resposta_de_infraestrutura(dados.get("message", "")):
                raise RespostaDeInfraestrutura(dados.get("message", "")[:120])
            return Resposta.de_dict(pergunta, dados, coletado_em=agora())

        raise RuntimeError(f"{MAX_TENTATIVAS} tentativas sem resposta: {pergunta[:60]!r}")

    @staticmethod
    def _ler_sse(resposta):
        for linha in resposta.iter_lines(decode_unicode=True):
            if linha and linha.startswith("data:"):
                dados = json.loads(linha[5:].strip())
                if "message" in dados:
                    return dados
        raise RuntimeError("stream terminou sem evento com 'message'")


class ClienteGravado:
    """Lê as respostas de golden/respostas.json. Modo padrão da suíte."""

    def __init__(self, gravacao: dict):
        self._respostas = {
            item["pergunta"]: Resposta.de_dict(item["pergunta"], item,
                                               item.get("coletado_em", ""))
            for item in gravacao.get("respostas", [])
        }
        self.coletado_em = gravacao.get("coletado_em", "")

    def perguntar(self, pergunta: str) -> Resposta:
        if pergunta not in self._respostas:
            raise KeyError(f"pergunta ausente na gravação: {pergunta!r}")
        return self._respostas[pergunta]

    def __contains__(self, pergunta):
        return pergunta in self._respostas


def agora() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
