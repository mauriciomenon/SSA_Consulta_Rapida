# Suite de testes - SSA Consulta Rapida

Testes do projeto em pytest. A contagem muda a cada commit; para ver a atual:
`uv run --no-sync pytest --collect-only -q | tail -1`.

## Como rodar

```bash
uv sync --frozen                       # ferramentas de desenvolvimento (grupo dev)
uv run --no-sync pytest -q             # suite completa
uv run --no-sync pytest -q tests/test_extracao.py   # um arquivo
uv run --no-sync pytest -q -m "not slow"            # por marcador
```

Nao ha pytest-xdist: `-n` nao funciona. Para conferir o resultado em script, use o
codigo de saida do pytest (nunca `|| true`).

## Configuracao (`pyproject.toml`)

- `testpaths = ["tests"]`; coleta `test_*.py` e `*_test.py`.
- Marcadores: `performance`, `integration`, `legacy`, `slow`, `smoke`, `stress`.

## Isolamento (`tests/conftest.py`)

- `SSA_RUNTIME_ROOT` aponta para uma pasta temporaria da sessao: logs
  (`ssa.log`, `ssa.json`) e `import_run_*.json` nunca vao para `logs/` do repositorio.
- `SSA_CONFIG_DIR` aponta para uma copia temporaria de `config/`, sem as
  preferencias locais da GUI.
- `QT_QPA_PLATFORM=offscreen` e `SSA_NON_INTERACTIVE=1`: GUI sem tela e CLI sem prompts.
- Um arquivo `.py` passado pelo nome que nao casa com `python_files` e recusado
  (scripts de `tests/` podem gravar no banco real).

## Pastas

- `_helpers/`: utilitarios compartilhados (banco temporario, harness de cenarios da GUI).
- `fixtures/`: arquivos de entrada dos testes.
- `scripts/`: testes de shell e PowerShell da guarda nativa (rodam a parte).
