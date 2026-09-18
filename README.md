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
tests/              os 4 blocos obrigatórios + testes dos extratores
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

Coleta de 18/09/2026, 56 respostas gravadas.

```
$ python -m pytest
5 failed, 250 passed, 86 skipped, 12 deselected
```

Log completo em `log-execucao.txt`.

As 5 falhas são os dois defeitos documentados em `relatorio.md`. Os `skipped`
são casos sem aquele tipo de fato esperado, mais os pares de fairness cegados
por F-02. Os `deselected` são os testes `live`.

Na primeira execução a suíte deu 28 falhas. 23 delas eram limitação dos
extratores, não defeito da AURA: a lista de frases de recusa não cobria
nenhuma das formas que ela realmente usa, a ancoragem contava a renda
informada na pergunta como valor inventado, e o comparador de fairness
reprovava por verbosidade. A calibração contra as respostas reais está
registrada nos commits.

## Falhas encontradas

Ver `relatorio.md`.
