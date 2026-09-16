# Suíte de testes da AURA — Projeto Final, Trilha 2

Disciplina *Testes Automatizados para Modelos de IA* — IEC PUC Minas
Sistema sob teste: **AURA**, assistente virtual RAG do Banco Aurora.

## Como rodar

```bash
pip install -r requirements.txt
python -m pytest
```

Roda contra `golden/respostas.json`, a gravação versionada. Não consome cota.

Contra o sistema no ar (consome cota da turma):

```bash
set AURA_USUARIO=grupo03
set AURA_SENHA=...
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

```
$ python -m pytest
...
```

*(colar a saída completa depois da coleta)*

Antes da coleta, os 32 testes que não dependem da gravação já rodam:

```
32 passed, 307 skipped, 12 deselected
```

Os `skipped` esperam `golden/respostas.json`. Os `deselected` são os `live`.

## Falhas encontradas

Ver `relatorio.md`.
