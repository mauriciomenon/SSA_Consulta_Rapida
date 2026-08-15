# Troubleshooting de Importacao (Baseline v4.43)

Guia ativo para diagnosticar falhas de importacao de planilhas.

## Fluxo de diagnostico

1. Identificar arquivo/lote com falha.
2. Coletar erro objetivo (log + stack + linha).
3. Classificar: extracao, validacao, persistencia, ou pos-processamento.
4. Corrigir por patch minimo e rerodar gates.

## Comandos uteis

```bash
# definir runtime alvo (padrao recomendado do repo)
PY_RUNTIME=3.13

# executar importacao pelo fluxo padrao
uv run --python "${PY_RUNTIME}" python main.py --force-rescan

# verificar testes focados de importacao
uv run --python "${PY_RUNTIME}" pytest -q tests/test_extracao.py
uv run --python "${PY_RUNTIME}" pytest -q tests/test_import_run_report.py

# checks de sanidade
uv run --python "${PY_RUNTIME}" python -m py_compile extracao/extractor.py
uv run --python "${PY_RUNTIME}" ruff check extracao/extractor.py
uv run --python "${PY_RUNTIME}" ty check extracao/extractor.py
```

## Causas comuns

### Falha ao ler planilha

- validar formato real do arquivo (`.xls/.xlsx`).
- checar permissao de leitura e arquivo bloqueado por outro processo.

### Nenhuma linha valida apos validacao

- conferir `numero_ssa` e campos obrigatorios no lote.
- conferir mapeamentos em `config/column_mappings.json`.

### Importacao concluida sem atualizacao

- confirmar se o lote tem dados novos ou alterados.
- em caso de duvida, executar full rescan.

### Estado "rebaixou" apos importar planilha

Checklist objetivo:

1. conferir `data_planilha` e `data_arquivo_origem` da linha existente e da linha nova
2. confirmar se o registro existente ja estava em `STE` ou `SCA` (deve bloquear update)
3. verificar se o arquivo novo tem timestamp confiavel:
   - se nao tiver, update de linha existente deve ser bloqueado
4. validar ordenacao da importacao explicita:
   - arquivo mais antigo deve entrar antes do mais novo

Consulta SQL util:

```sql
SELECT
  numero_ssa,
  situacao,
  data_cadastro,
  data_planilha,
  data_arquivo_origem,
  arquivo_origem
FROM ssas
WHERE numero_ssa IN ('202600654');
```

### Arquivo valido com nome generico nao atualiza

Comportamento esperado:

1. se nao houver data no nome, pipeline usa `mtime/ctime`
2. se nao houver timestamp confiavel, arquivo ainda pode inserir novos
3. sem timestamp confiavel, nao deve sobrescrever linha existente

## Regras de seguranca operacional

1. Nao aplicar suppress silencioso em erro de extracao/validacao.
2. Nao mudar regra de schema sem registrar no backlog e handoff.
3. Nao assumir fallback caro sem medicao objetiva.

## Evidencia e rastreabilidade

- Registrar no minimo:
  1. nome do arquivo de entrada
  2. tipo de erro
  3. comando executado
  4. resultado do teste focado
  5. commit de correcao

## Testes de regressao recomendados

```bash
uv run --python 3.13 python -m pytest -q \
  tests/test_upsert_behaviors.py \
  tests/test_import_run_report.py \
  tests/test_database_optimized_alias_views.py
```

<!-- DOC_SYNC_MAC: 2026-03-30 contract-aligned -->

