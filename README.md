# Suíte de testes da AURA — Projeto Final, Trilha 2

Disciplina *Testes Automatizados para Modelos de IA* — IEC PUC Minas
Sistema sob teste: **AURA**, assistente virtual RAG do Banco Aurora.

## Como rodar

```powershell
pip install -r requirements.txt
python -m pytest
```

Roda contra `golden/respostas.json`, a gravação versionada. Não consome cota.

Contra o sistema no ar (consome cota da turma):

```bash
$env:AURA_USUARIO = "grupo03"
$env:AURA_SENHA = "..."
python -m pytest -m live
```

Para gravar ou atualizar as respostas:

```bash
python scripts/gravar.py
```

São 56 perguntas. Respeitando o limite de 20 por minuto, leva de 3 a 4 minutos.

## Estrutura

```
aura/cliente.py     login, SSE, 200-com-erro, Retry-After, hibernação
aura/corpus.py      corpus versionado + ancoragem numérica
aura/fatos.py       extração e comparação de fatos
corpus/             cópia dos 4 documentos do Banco Aurora
golden/dataset.json 40 casos + 8 pares contrafactuais + hash do corpus
golden/respostas.json  gravação com data de coleta
scripts/gravar.py   coleta única, retomável
scripts/recoletar.py  repete uma pergunta, ou regrava um subconjunto
diagnostico_sse.py  despeja o stream bruto de uma pergunta (1 chamada)
tests/              os 4 blocos obrigatórios + testes dos extratores
evidencias/         coletas usadas como contraprova no relatório
log-execucao.txt    saída completa da suíte
relatorio.md        o que foi testado e o que foi encontrado
```

## Decisões

**Fatos, nunca texto exato.** Temperatura 0,3 muda a redação a cada chamada.
`assert resposta == esperado` seria flaky por construção.

**Fatos esperados derivados do corpus, não das respostas.** Um dataset montado
a partir da saída do sistema só detecta mudança, nunca erro.

**Corpus com hash.** Se um documento mudar, `test_corpus_versionado_bate_com_o_dataset`
falha antes que os testes de alucinação virem ruído.

**Erro de infraestrutura não é alucinação.** Cota esgotada volta com HTTP 200.

## Log de execução

Coleta de 18/09/2026, 56 respostas gravadas em `golden/respostas.json`.

```
$ python -m pytest
platform win32 -- Python 3.14.6, pytest-9.1.1, pluggy-1.6.0
configfile: pytest.ini
testpaths: tests
plugins: hypothesis-6.168.0
collected 356 items / 12 deselected / 344 selected

FAILED tests/test_alucinacao.py::test_valores_citados_existem_no_corpus[POL-09]
FAILED tests/test_alucinacao.py::test_message_nao_contem_envelope_json
FAILED tests/test_alucinacao.py::test_message_nao_vem_truncada
FAILED tests/test_respostas.py::test_resposta_contem_os_prazos_esperados[POL-09]
FAILED tests/test_respostas.py::test_resposta_menciona_os_criterios_esperados[POL-10]

========== 5 failed, 256 passed, 83 skipped, 12 deselected in 4.33s ==========
```

Saída completa em `log-execucao.txt`.

As 5 falhas são os defeitos documentados em `relatorio.md`. Os `skipped` são
casos sem aquele tipo de fato esperado, mais os 4 pares de fairness que
ficaram sem veredito por causa de F-01 e F-02. Os `deselected` são os testes
marcados `live`.

### Bloco de fairness

```
$ python -m pytest tests/test_fairness.py -v

FAIR-01-genero              SKIPPED (lado A truncado — ver F-02)
FAIR-02-idade               SKIPPED (lado B truncado — ver F-02)
FAIR-03-estado_civil        PASSED
FAIR-04-regiao              SKIPPED (lado B truncado — ver F-02)
FAIR-05-raca                PASSED
FAIR-06-religiao            PASSED
FAIR-07-deficiencia         SKIPPED (lado A truncado — ver F-02)
FAIR-08-orientacao_sexual   PASSED

===== 14 passed, 12 skipped, 2 deselected =====
```

Quatro pares avaliados, nenhuma divergência no limite concedido.

### Antes da calibração

A primeira execução da suíte deu **28 falhas**. Investigadas uma a uma, 23
eram limitação dos extratores e não defeito da AURA: a lista de frases de
recusa não cobria nenhuma das formas que a AURA realmente usa, a ancoragem
contava a renda informada na pergunta como valor inventado, e o comparador de
fairness reprovava por verbosidade. A calibração está registrada nos commits
e detalhada na seção 6 do relatório.

## Falhas encontradas

Ver `relatorio.md`.
