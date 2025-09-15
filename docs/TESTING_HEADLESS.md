# Testes Headless e Execução Rápida

Este guia resume como rodar a suíte de testes, validar importação de dados e executar verificações rápidas em modo headless (sem UI) tanto no Terminal integrado do VS Code quanto no Terminal.app (macOS).

## 1. Pré‑requisitos
- Python (pyenv) conforme versão definida no projeto (ex: 3.13.x).
- Dependências instaladas: `pip install -e .` ou `pip install -r requirements.txt`.
- Variáveis opcionais de ambiente (nenhuma crítica obrigatória para os testes de núcleo).

## 2. Script Unificado
Use o script `scripts/run_tests.sh`:

```
./scripts/run_tests.sh          # modo quiet (rápido)
./scripts/run_tests.sh full     # verbose (-vv)
./scripts/run_tests.sh debug    # verbose + mostra prints (-s)
./scripts/run_tests.sh cov      # com coverage
```

Passar filtros adicionais:
```
PYTEST_ADDOPTS="-k upsert" ./scripts/run_tests.sh debug
```

## 3. Execução Headless (Qt)
O arquivo `tests/conftest.py` força `QT_QPA_PLATFORM=offscreen` para evitar abertura de janelas. Caso precise reforçar manualmente:
```
QT_QPA_PLATFORM=offscreen ./scripts/run_tests.sh full
```

## 4. Diagnóstico Rápido
| Situação | Ação |
|----------|------|
| Coleta vazia (0 tests) | Verificar se houve interrupção (Ctrl+C) ou plugin travando; rodar `pytest -vv -s tests/test_upsert_behaviors.py`. |
| Teste específico | `pytest tests/test_upsert_behaviors.py::test_upsert_insert_new -vv -s` |
| Ver lista de arquivos candidatos | `python - <<'PY'` com varredura AST (exemplo no histórico). |
| Limpar cache | `pytest --cache-clear -q` |

## 5. Cobertura
Gera relatório em terminal:
```
./scripts/run_tests.sh cov
```
Para HTML (se desejar):
```
coverage html && open htmlcov/index.html
```

## 6. Boas Práticas
- Rodar `full` antes de abrir PR para captar avisos.
- Usar `debug` para investigar prints temporários (removê-los depois).
- Evitar manter prints de depuração permanentes em testes (ruído na saída CI).

## 7. Limpeza de Artefatos
- Cache pytest: `.pytest_cache/`
- Cobertura: `.coverage` e `htmlcov/`
- Databases temporários criados em `tmp_path` (pytest limpa automaticamente)

## 8. Erros Frequentes
| Erro | Causa | Correção |
|------|-------|----------|
| TOML parse error | Bloco inválido no `pyproject.toml` | Corrigir/Remover docstring multi‑linha fora do padrão TOML |
| ImportError antigo | Test deletado ainda no cache | `pytest --cache-clear` + remover `__pycache__` se necessário |
| 0 items collected | Interrupção/KeyboardInterrupt ou plugin | Reexecutar sem interrupção, isolar test file |

## 9. Execução no Terminal.app
```
cd /caminho/para/SSA_Consulta_Rapida
pyenv local 3.13.7   # se usar pyenv
pip install -r requirements.txt
./scripts/run_tests.sh full
```

## 10. Fluxo Sugerido Pré-Release
1. `./scripts/run_tests.sh full`
2. `./scripts/run_tests.sh cov` (opcional, checar % cobertura)
3. Verificar ausência de prints de debug.
4. Rodar ferramenta de lint (Ruff) se necessário.

---
Documento gerado para padronizar execuções consistentes e reduzir atrito em diagnósticos.
