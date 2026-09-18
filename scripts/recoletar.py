"""Recoleta dirigida: confirma uma falha por repetição, ou regrava um subconjunto.

Uma execução é anedota. Este script existe para as duas coisas que faltam
depois da coleta inicial: confirmar que uma falha se repete, e regravar os
casos que vieram contaminados pelo defeito de formato.

    # confirma F-03: repete a pergunta do POL-10 três vezes, sem gravar
    python scripts/recoletar.py --repetir POL-10 --vezes 3

    # regrava os 16 casos dos pares contrafactuais
    python scripts/recoletar.py --fairness

Custo: 1 chamada por pergunta, respeitando o limite de 20 por minuto.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from datetime import datetime, timezone

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from aura import fatos  # noqa: E402
from aura.cliente import ClienteAura, RespostaDeInfraestrutura  # noqa: E402

DATASET = RAIZ / "golden" / "dataset.json"
RESPOSTAS = RAIZ / "golden" / "respostas.json"
LIMITE_SEGUIDAS = 3


def carregar_dataset():
    return json.loads(DATASET.read_text(encoding="utf-8"))


def salvar(gravacao):
    gravacao["coletado_em"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    RESPOSTAS.write_text(
        json.dumps(gravacao, ensure_ascii=False, indent=2), encoding="utf-8")


def diagnostico(mensagem: str) -> str:
    marcas = []
    if fatos.envelope_json_vazado(mensagem):
        marcas.append("ENVELOPE")
    if fatos.parece_truncada(mensagem):
        marcas.append("TRUNCADA")
    return " ".join(marcas) or "ok"


# ---------------------------------------------------------------------------
# modo 1: repetir uma pergunta para confirmar que a falha não é anedota
# ---------------------------------------------------------------------------


def repetir(id_caso: str, vezes: int) -> int:
    dados = carregar_dataset()
    caso = next((c for c in dados["casos"] if c["id"] == id_caso), None)
    if caso is None:
        print(f"caso {id_caso!r} não existe no dataset")
        return 1

    marcadores = caso["fatos_esperados"]["marcadores"]
    print(f"{id_caso}: {caso['pergunta']}")
    print(f"marcadores esperados: {marcadores}\n")

    cliente = ClienteAura()
    if not cliente.acordar():
        print("servidor não acordou")
        return 1

    reprovou = 0
    for tentativa in range(1, vezes + 1):
        try:
            resposta = cliente.perguntar(caso["pergunta"])
        except RespostaDeInfraestrutura as erro:
            print(f"[{tentativa}/{vezes}] INFRA: {erro}")
            return 1
        util = fatos.texto_util(resposta.message)
        ausentes = [m for m in marcadores if not fatos.menciona_flexivel(util, m)]
        if ausentes:
            reprovou += 1
        print(f"[{tentativa}/{vezes}] {diagnostico(resposta.message):18} "
              f"len={len(resposta.message):3} ausentes={ausentes}")
        print(f"        {util[:200]}\n")

    print(f"=== a falha se repetiu em {reprovou}/{vezes} execuções")
    if reprovou == vezes:
        print("    padrão consistente: promova a falha confirmada no relatório")
    elif reprovou == 0:
        print("    não reproduziu: remova o achado ou reclassifique")
    else:
        print("    intermitente: registre a taxa no relatório, é o dado honesto")
    return 0


# ---------------------------------------------------------------------------
# modo 2: regravar os casos dos pares de fairness
# ---------------------------------------------------------------------------


def regravar_fairness(tentativas: int = 3) -> int:
    dados = carregar_dataset()
    alvo = []
    for par in dados["pares_fairness"]:
        alvo.extend([par["a"], par["b"]])

    gravacao = json.loads(RESPOSTAS.read_text(encoding="utf-8"))
    antes = len(gravacao["respostas"])
    gravacao["respostas"] = [r for r in gravacao["respostas"]
                             if r["pergunta"] not in alvo]
    print(f"removendo {antes - len(gravacao['respostas'])} resposta(s) dos pares")
    print(f"recoletando {len(alvo)} pergunta(s) — ~{len(alvo) * 3.5 / 60:.1f} min\n")

    cliente = ClienteAura()
    if not cliente.acordar():
        print("servidor não acordou")
        return 1

    seguidas, limpas, chamadas = 0, 0, 0
    for i, pergunta in enumerate(alvo, 1):
        # repete enquanto vier malformada: sem os dois lados íntegros não há
        # veredito de fairness. O número de tentativas vai para o relatório,
        # porque ele mede a frequência de F-01 nessas perguntas.
        melhor, estado = None, "?"
        for tentativa in range(1, tentativas + 1):
            try:
                resposta = cliente.perguntar(pergunta)
                chamadas += 1
            except RespostaDeInfraestrutura as erro:
                print(f"[{i}/{len(alvo)}] INFRA: {erro}")
                seguidas += 1
                break
            seguidas = 0
            estado = diagnostico(resposta.message)
            if melhor is None or estado == "ok":
                melhor = resposta
            if estado == "ok":
                limpas += 1
                print(f"[{i}/{len(alvo)}] ok  (tentativa {tentativa}) "
                      f"len={len(resposta.message):3} {pergunta[:45]!r}")
                break
        else:
            print(f"[{i}/{len(alvo)}] {estado:18} após {tentativas} tentativas "
                  f"{pergunta[:45]!r}")

        if seguidas >= LIMITE_SEGUIDAS:
            print("\ncota acabou; rode mais tarde para completar")
            break
        if melhor is not None:
            gravacao["respostas"].append(melhor.para_dict())
            salvar(gravacao)

    print(f"\n{limpas}/{len(alvo)} resposta(s) limpas · {chamadas} chamada(s) gastas")
    print("rode `python -m pytest tests/test_fairness.py -v` para ver os vereditos")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repetir", metavar="ID",
                        help="id do caso a repetir (ex.: POL-10)")
    parser.add_argument("--vezes", type=int, default=3)
    parser.add_argument("--fairness", action="store_true",
                        help="regrava os 16 casos dos pares contrafactuais")
    parser.add_argument("--tentativas", type=int, default=3,
                        help="quantas vezes repetir uma pergunta malformada")
    args = parser.parse_args()

    if args.repetir:
        return repetir(args.repetir, args.vezes)
    if args.fairness:
        return regravar_fairness(args.tentativas)
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
