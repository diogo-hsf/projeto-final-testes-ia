"""Grava as respostas reais da AURA uma vez, para a suíte rodar em replay.

    set AURA_USUARIO=grupo03
    set AURA_SENHA=...
    python scripts/gravar.py              grava só o que falta
    python scripts/gravar.py --regravar   grava tudo de novo

Salva a cada resposta: se parar no meio, rodar de novo retoma de onde parou.
"""
from __future__ import annotations

import json
import pathlib
import sys
from datetime import datetime, timezone

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from aura.cliente import ClienteAura, RespostaDeInfraestrutura  # noqa: E402

DATASET = RAIZ / "golden" / "dataset.json"
RESPOSTAS = RAIZ / "golden" / "respostas.json"
LIMITE_SEGUIDAS = 3   # falhas de infra em sequência antes de desistir


def perguntas_do_dataset():
    dados = json.loads(DATASET.read_text(encoding="utf-8"))
    vistas = []
    for caso in dados["casos"]:
        if caso["pergunta"] not in vistas:
            vistas.append(caso["pergunta"])
    for par in dados["pares_fairness"]:
        for lado in ("a", "b"):
            if par[lado] not in vistas:
                vistas.append(par[lado])
    return vistas


def salvar(gravacao):
    gravacao["coletado_em"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    gravacao["modelo"] = "gemini-3.6-flash, temperatura 0.3 (backend/config.json)"
    RESPOSTAS.write_text(
        json.dumps(gravacao, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    regravar = "--regravar" in sys.argv
    if RESPOSTAS.exists() and not regravar:
        gravacao = json.loads(RESPOSTAS.read_text(encoding="utf-8"))
    else:
        gravacao = {"respostas": []}

    ja_tem = {r["pergunta"] for r in gravacao["respostas"]}
    pendentes = [p for p in perguntas_do_dataset() if p not in ja_tem]

    print(f"{len(pendentes)} pergunta(s) a gravar")
    if not pendentes:
        print("nada a fazer; use --regravar para refazer a coleta")
        return 0
    print(f"estimativa: ~{len(pendentes) * 3.5 / 60:.1f} min\n")

    cliente = ClienteAura()
    if not cliente.acordar():
        print("servidor não acordou; tente de novo em alguns minutos")
        return 1

    falhas = 0
    seguidas = 0   # falhas de infra em sequência: cota da turma acabou
    for i, pergunta in enumerate(pendentes, 1):
        try:
            resposta = cliente.perguntar(pergunta)
        except RespostaDeInfraestrutura as erro:
            print(f"[{i}/{len(pendentes)}] INFRA  {pergunta[:55]!r}: {erro}")
            falhas += 1
            seguidas += 1
            if seguidas >= LIMITE_SEGUIDAS:
                print(f"\n{LIMITE_SEGUIDAS} falhas de infra seguidas: a cota acabou.")
                print("Parando para não desperdiçar chamada. Rode mais tarde.")
                break
            continue
        except Exception as erro:  # noqa: BLE001
            print(f"[{i}/{len(pendentes)}] ERRO   {pergunta[:55]!r}: {erro}")
            falhas += 1
            continue

        seguidas = 0
        gravacao["respostas"].append(resposta.para_dict())
        salvar(gravacao)
        print(f"[{i}/{len(pendentes)}] ok     {pergunta[:55]!r}")

    print(f"\n{len(gravacao['respostas'])} resposta(s) em golden/respostas.json")
    if falhas:
        print(f"{falhas} falha(s) de coleta; rode de novo para retomar o que falta")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
