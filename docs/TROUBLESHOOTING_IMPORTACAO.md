# Troubleshooting de Importacao (Baseline v4.32)

Guia ativo para diagnosticar falhas de importacao de planilhas.

## Fluxo de diagnostico

1. Identificar arquivo/lote com falha.
2. Coletar erro objetivo (log + stack + linha).
3. Classificar: extracao, validacao, persistencia, ou pos-processamento.
4. Corrigir por patch minimo e rerodar gates.

## Comandos uteis

```bash
# executar importacao pelo fluxo padrao
uv run --python 3.13 python main.py --force-rescan

# verificar testes focados de importacao
uv run --python 3.13 pytest -q tests/test_extracao.py
uv run --python 3.13 pytest -q tests/test_import_run_report.py

# checks de sanidade
uv run --python 3.13 python -m py_compile extracao/extractor.py
uv run --python 3.13 ruff check extracao/extractor.py
uv run --python 3.13 ty check extracao/extractor.py
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
