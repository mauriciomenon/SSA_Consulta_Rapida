# Testes Headless e Execucao Rapida

Este guia resume como rodar a suite de testes, validar importacao de dados e executar verificacoes rapidas em modo headless (sem UI) tanto no Terminal integrado do VS Code quanto no Terminal.app (macOS).

## 1. Pre‐requisitos
- Python (pyenv) conforme versao definida no projeto (ex: 3.13.x).
- Dependencias instaladas: `pip install -e .` ou `pip install -r requirements.txt`.
- Variaveis opcionais de ambiente (nenhuma critica obrigatoria para os testes de nucleo).

## 2. Script Unificado
Use o script `scripts/run_tests.sh`:

```
./scripts/run_tests.sh          # modo quiet (rapido)
./scripts/run_tests.sh full     # verbose (-vv)
./scripts/run_tests.sh debug    # verbose + mostra prints (-s)
./scripts/run_tests.sh cov      # com coverage
```

Passar filtros adicionais:
```
PYTEST_ADDOPTS="-k upsert" ./scripts/run_tests.sh debug
```

## 3. Execucao Headless (Qt)
O arquivo `tests/conftest.py` forca `QT_QPA_PLATFORM=offscreen` para evitar abertura de janelas. Caso precise reforcar manualmente:
```
QT_QPA_PLATFORM=offscreen ./scripts/run_tests.sh full
```

### Teste grafico automatico dos filtros GUI

Para validar cliques reais da GUI, resumo visual de filtros, chips do resumo e
indicadores de filtros por coluna em modo automatico/headless:

```
QT_QPA_PLATFORM=offscreen SSA_SYNC_FILTER=1 uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "graphical or filters_summary or column_filter_buttons_flow or gui_smoke or hard_reset_filters_state"
```

## 4. Diagnostico Rapido
| Situacao | Acao |
|----------|------|
| Coleta vazia (0 tests) | Verificar se houve interrupcao (Ctrl+C) ou plugin travando; rodar `pytest -vv -s tests/test_upsert_behaviors.py`. |
| Teste especifico | `pytest tests/test_upsert_behaviors.py::test_upsert_insert_new -vv -s` |
| Ver lista de arquivos candidatos | `python - <<'PY'` com varredura AST (exemplo no historico). |
| Limpar cache | `pytest --cache-clear -q` |

## 5. Cobertura
Gera relatorio em terminal:
```
./scripts/run_tests.sh cov
```
Para HTML (se desejar):
```
coverage html && open htmlcov/index.html
```

## 6. Boas Praticas
- Rodar `full` antes de abrir PR para captar avisos.
- Usar `debug` para investigar prints temporarios (remove-los depois).
- Evitar manter prints de depuracao permanentes em testes (ruido na saida CI).

## 7. Limpeza de Artefatos
- Cache pytest: `.pytest_cache/`
- Cobertura: `.coverage` e `htmlcov/`
- Databases temporarios criados em `tmp_path` (pytest limpa automaticamente)

## 8. Erros Frequentes
| Erro | Causa | Correcao |
|------|-------|----------|
| TOML parse error | Bloco invalido no `pyproject.toml` | Corrigir/Remover docstring multi‐linha fora do padrao TOML |
| ImportError antigo | Test deletado ainda no cache | `pytest --cache-clear` + remover `__pycache__` se necessario |
| 0 items collected | Interrupcao/KeyboardInterrupt ou plugin | Reexecutar sem interrupcao, isolar test file |

## 9. Execucao no Terminal.app
```
cd /caminho/para/SSA_Consulta_Rapida
pyenv local 3.13.12  # se usar pyenv
pip install -r requirements.txt
./scripts/run_tests.sh full
```

## 10. Fluxo Sugerido Pre-Release
1. `./scripts/run_tests.sh full`
2. `./scripts/run_tests.sh cov` (opcional, checar % cobertura)
3. Verificar ausencia de prints de debug.
4. Rodar ferramenta de lint (Ruff) se necessario.

---
Documento gerado para padronizar execucoes consistentes e reduzir atrito em diagnosticos.

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->
