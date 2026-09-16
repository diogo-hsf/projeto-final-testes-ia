# Relatório — Suíte de testes da AURA

**Disciplina:** Testes Automatizados para Modelos de IA — IEC PUC Minas
**Trilha:** 2 (LLM/RAG)
**Autor:** Diogo Ferreira
**Data:** \_\_/09/2026
**Sistema sob teste:** AURA — assistente virtual RAG do Banco Aurora
**Coleta das respostas:** *(preencher com o `coletado_em` de `golden/respostas.json`)*

---

## 1. O que foi testado, e por quê

A AURA é um sistema sem oráculo determinístico: temperatura 0,3, mesma
pergunta com redações diferentes, e nenhuma "resposta certa" única contra a
qual comparar. Toda a estratégia da suíte decorre disso.

| Bloco | Pergunta que o bloco responde | Arquivo |
|---|---|---|
| 1. Avaliação de respostas | O fato certo aparece? A fonte sustenta? Fica no escopo? | `tests/test_respostas.py` |
| 2. Alucinação | Recusa o que não sabe? Todo número citado existe no corpus? | `tests/test_alucinacao.py` |
| 3. Fairness | Trocar um atributo sensível muda o fato? | `tests/test_fairness.py` |
| 4. Regressão de prompts | O sistema mudou desde a coleta? O dataset é íntegro? | `tests/test_regressao_prompts.py` |
| — Ferramentas | Os extratores medem o que dizem medir? | `tests/test_ferramentas.py` |

### O oráculo que escolhemos

Comparar texto seria testar a redação do LLM, não o comportamento do sistema.
Comparamos **fatos extraídos**: valor em R$, percentual, prazo em dias e em
meses, documento citado em `sources`, e dois vereditos binários (declarou
indisponibilidade? prometeu aprovação?).

A ancoragem da alucinação é feita contra `corpus/`, cópia versionada dos
quatro documentos, com hash conferido a cada execução.

---

## 2. Cobertura

- **40 casos** no golden dataset: 28 de resposta fundamentada, 8 de
  alucinação, 4 adversariais.
- **8 pares contrafactuais** de fairness: gênero, idade, estado civil, região,
  raça, religião, deficiência e orientação sexual.
- **363 testes** coletados.

---

## 3. Falhas encontradas

> Modelo a repetir para cada falha. A estrutura segue o que o professor cobra:
> o teste que falha, a evidência medida, a causa raiz e o impacto.

### F-01 — *(título curto do defeito)*

**Teste que falha**
`tests/test_XXX.py::test_nome_do_teste[ID-DO-CASO]`

**Pergunta**
> *(a pergunta exata enviada ao `/chat`)*

**Resposta recebida** *(coletada em AAAA-MM-DD)*
> *(o texto da resposta, e o conteúdo de `sources`)*

**Evidência medida**
*(o número, não a impressão. Ex.: "o par contrafactual de raça divergiu em 3
de 3 repetições, com limites de R$ 2.500 e R$ 1.200")*

**Causa raiz**
*(o mecanismo. Ex.: o recuperador trouxe o chunk certo, mas o gerador
completou com um valor do próprio treino — quadrante faithfulness baixa /
context recall alto)*

**Impacto**
*(o que custa para o cliente do Banco Aurora e para o banco)*

---

## 4. Testes que passam

*(Parte do sistema está correta, e dizer o que está certo é parte do
trabalho. Listar aqui os blocos que passaram integralmente.)*

---

## 5. Limitações desta suíte

*(Ser explícito aqui vale mais que fingir cobertura total.)*

- Os extratores de fato cobrem valor em R$, percentual e prazo. Critérios
  expressos só em prosa dependem de marcador textual, que é mais frágil.
- O corpus é pequeno e o `rag_score_threshold` é 0,0, então `sources` quase
  sempre traz vários documentos. `sources` cobre o recuperador, não prova que
  o gerador usou aquele trecho.
- A suíte roda contra uma gravação. Ela responde "como o sistema se comportou
  em *(data)*", e os testes `live` são o que detecta mudança desde então.
- Repetições: *(dizer quantas vezes cada falha foi confirmada — uma execução
  só é anedota)*.

---

## 6. Como reproduzir

```bash
pip install -r requirements.txt
pytest                       # replay, não consome cota
pytest -m live               # contra o sistema no ar
```

Log completo em `evidencias/`.
