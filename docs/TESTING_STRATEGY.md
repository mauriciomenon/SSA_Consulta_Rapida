# Estrategia de Testes

> Versao inicial – iterativa. Atualizar conforme novos modulos forem cobertos.

## Piramide de Testes (Alvo)
- Unidade (rapidos, puros, sem IO pesado) ~60%
- Integracao (SQLite + scripts + normalizacao) ~30%
- End-to-End / Gates (run_quality_gates, smoke CLI/GUI) ~10%

## Classes de Testes Atuais
| Tipo | Exemplos | Observacoes |
|------|----------|-------------|
| Unidade | (a ser expandido) funcoes de normalizacao isoladas | Criar camada unit para `_normalize_numero_ssa_value` etc. |
| Integracao | `test_import_dtypes.py`, `test_db_upsert_integrity.py`, `test_normalization_rules.py` | Usam fixtures de DB temporario e DataFrames sinteticos |
| Governaca / Gates | `test_quality_gates_smoke.py`, `test_quality_gates_fail_paths.py` | Validam o pipeline de qualidade em ambos caminhos |
| Compatibilidade Legacy | `test_import_single_legacy_compat.py` | Substitui testes antigos ruidosos |
| Referencia Legacy (skipped) | `tests/legacy_tests/*` placeholders | Mantidos apenas por historico (skip module-level) |

## Fixtures Principais
- `temp_db`: cria banco SQLite isolado a partir de `config/schema.sql` (ou otimizado quando aplicavel)
- `sample_import_dataframe`: DataFrame sintetico base para casos de import
- `sample_upsert_batches`: Lotes ordenados para exercitar atualizacao condicional (upsert inteligente)
- `normalization_cases`: Casos parametrizados (entrada → saida) para normalizacao de `numero_ssa`

## Politica de Dtypes
Matriz centralizada em `tests/_helpers/dtypes_matrix.py` define:
- `expected_dtype`
- Flags (ex.: `required`, `normalized`)
Testes devem importar a matriz, nunca reescrever os tipos manualmente.

## Quality Gates
Scripts agregados por `run_quality_gates.py`:
- `validate_configs.py` (estrutura & semantica leve)
- `smoke_cli.py` (entrada CLI basica, marker `SSA_SMOKE_TEST`)
- `check_docs.py` (densidade minima + placeholders)

O agregador oferece JSON com `summary.overall_status` e lista de `gates`. Argumentos adicionais suportados:
```
uv run --python 3.13 scripts/run_quality_gates.py --only smoke_cli
uv run --python 3.13 scripts/run_quality_gates.py --extra-doc docs/README.md
uv run --python 3.13 scripts/run_quality_gates.py --skip check_docs
```

## Markers Pytest
Definidos em `pytest.ini`:
- `integration`
- `legacy`
- `slow`
- `smoke`

Uso rapido:
```
pytest -m "integration and not slow" -q
pytest -m smoke -q
```

## Limiar Progressivo de Qualidade (Roadmap)
| Fase | Criterios | Acao de Bloqueio |
|------|-----------|------------------|
| Fase 1 | >=5 testes core integracao (OK) + gates smoke passando | CI falha se <5 |
| Fase 2 | Cobertura >=30% modulos criticos (`armazenamento/`, `core/`) | CI marca warning se <30% |
| Fase 3 | Cobertura >=60%, + testes unit para normalizacao e cache | CI falha se <60% |
| Fase 4 | Cobertura >=80%, lint estrito (sem noqa novo) | PR bloqueado |

(Percentuais atuais ainda em medicao – primeira coleta manual via `pytest --cov`.)

## Proximos Incrementos Planejados
1. Adicionar testes unit para funcoes de normalizacao (sem criar DB).
2. Cobrir caminhos de erro de `insert_dataframe_with_smart_upsert` (linhas de regressao futuras).
3. Teste de idempotencia de `verify_database_integrity` em base consistente.
4. Cobrir `config_manager` leitura com mock de diretorio alternativo (`SSA_CONFIG_DIR`).
5. Integrar relatorio de cobertura ao pipeline CI (HTML opcional em artefatos).

## Convencoes
- Evitar `print` em testes novos (usar asserts). Legacy placeholders podem conter prints, mas estao skipped.
- Nunca depender de arquivos reais grandes em `docs_entrada/` para caminhos core.
- Em falhas de subprocessos, sempre exibir stdout/stderr no assert para diagnostico.

## Execucao Rapida
```
# Smoke + integracao basica (exclui legacy/slow)
pytest -m "integration and not slow and not legacy" -q

# Gates (caminho feliz + falhas controladas)
pytest -k quality_gates -q

# Cobertura inicial
pytest --cov=armazenamento --cov=core --cov-report=term-missing -q
```

## Politica de Migracao Legacy
Criterios (ja aplicados): fluxo suportado, assert nao redundante, sem dependencia obsoleta, tempo <2s. Testes fora dos criterios: convertidos em placeholder com `pytest.skip` no import modulo.

## Falhas Esperadas / Negative Paths
Documentados em `test_quality_gates_fail_paths.py` – nao remover sem adicionar substituto equivalentes de governanca.

---
Atualize este documento ao:
- Introduzir novo marcador ou fixture
- Elevar fase de cobertura
- Deprecar scripts de gate ou alterar saida JSON

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->

