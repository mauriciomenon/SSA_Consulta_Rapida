# Estratégia de Testes

> Versão inicial – iterativa. Atualizar conforme novos módulos forem cobertos.

## Pirâmide de Testes (Alvo)
- Unidade (rápidos, puros, sem IO pesado) ~60%
- Integração (SQLite + scripts + normalização) ~30%
- End-to-End / Gates (run_quality_gates, smoke CLI/GUI) ~10%

## Classes de Testes Atuais
| Tipo | Exemplos | Observações |
|------|----------|-------------|
| Unidade | (a ser expandido) funções de normalização isoladas | Criar camada unit para `_normalize_numero_ssa_value` etc. |
| Integração | `test_import_dtypes.py`, `test_db_upsert_integrity.py`, `test_normalization_rules.py` | Usam fixtures de DB temporário e DataFrames sintéticos |
| Governaça / Gates | `test_quality_gates_smoke.py`, `test_quality_gates_fail_paths.py` | Validam o pipeline de qualidade em ambos caminhos |
| Compatibilidade Legacy | `test_import_single_legacy_compat.py` | Substitui testes antigos ruidosos |
| Referência Legacy (skipped) | `tests/legacy_tests/*` placeholders | Mantidos apenas por histórico (skip module-level) |

## Fixtures Principais
- `temp_db`: cria banco SQLite isolado a partir de `config/schema.sql` (ou otimizado quando aplicável)
- `sample_import_dataframe`: DataFrame sintético base para casos de import
- `sample_upsert_batches`: Lotes ordenados para exercitar atualização condicional (upsert inteligente)
- `normalization_cases`: Casos parametrizados (entrada → saída) para normalização de `numero_ssa`

## Política de Dtypes
Matriz centralizada em `tests/_helpers/dtypes_matrix.py` define:
- `expected_dtype`
- Flags (ex.: `required`, `normalized`)
Testes devem importar a matriz, nunca reescrever os tipos manualmente.

## Quality Gates
Scripts agregados por `run_quality_gates.py`:
- `validate_configs.py` (estrutura & semântica leve)
- `smoke_cli.py` (entrada CLI básica, marker `SSA_SMOKE_TEST`)
- `check_docs.py` (densidade mínima + placeholders)

O agregador oferece JSON com `summary.overall_status` e lista de `gates`. Argumentos adicionais suportados:
```
python scripts/run_quality_gates.py --only smoke_cli
python scripts/run_quality_gates.py --extra-doc docs/README.md
python scripts/run_quality_gates.py --skip check_docs
```

## Markers Pytest
Definidos em `pytest.ini`:
- `integration`
- `legacy`
- `slow`
- `smoke`

Uso rápido:
```
pytest -m "integration and not slow" -q
pytest -m smoke -q
```

## Limiar Progressivo de Qualidade (Roadmap)
| Fase | Critérios | Ação de Bloqueio |
|------|-----------|------------------|
| Fase 1 | >=5 testes core integração (OK) + gates smoke passando | CI falha se <5 |
| Fase 2 | Cobertura >=30% módulos críticos (`armazenamento/`, `core/`) | CI marca warning se <30% |
| Fase 3 | Cobertura >=60%, + testes unit para normalização e cache | CI falha se <60% |
| Fase 4 | Cobertura >=80%, lint estrito (sem noqa novo) | PR bloqueado |

(Percentuais atuais ainda em medição – primeira coleta manual via `pytest --cov`.)

## Próximos Incrementos Planejados
1. Adicionar testes unit para funções de normalização (sem criar DB).
2. Cobrir caminhos de erro de `insert_dataframe_with_smart_upsert` (linhas de regressão futuras).
3. Teste de idempotência de `verify_database_integrity` em base consistente.
4. Cobrir `config_manager` leitura com mock de diretório alternativo (`SSA_CONFIG_DIR`).
5. Integrar relatório de cobertura ao pipeline CI (HTML opcional em artefatos).

## Convenções
- Evitar `print` em testes novos (usar asserts). Legacy placeholders podem conter prints, mas estão skipped.
- Nunca depender de arquivos reais grandes em `docs_entrada/` para caminhos core.
- Em falhas de subprocessos, sempre exibir stdout/stderr no assert para diagnóstico.

## Execução Rápida
```
# Smoke + integração básica (exclui legacy/slow)
pytest -m "integration and not slow and not legacy" -q

# Gates (caminho feliz + falhas controladas)
pytest -k quality_gates -q

# Cobertura inicial
pytest --cov=armazenamento --cov=core --cov-report=term-missing -q
```

## Política de Migração Legacy
Critérios (já aplicados): fluxo suportado, assert não redundante, sem dependência obsoleta, tempo <2s. Testes fora dos critérios: convertidos em placeholder com `pytest.skip` no import módulo.

## Falhas Esperadas / Negative Paths
Documentados em `test_quality_gates_fail_paths.py` – não remover sem adicionar substituto equivalentes de governança.

---
Atualize este documento ao:
- Introduzir novo marcador ou fixture
- Elevar fase de cobertura
- Deprecar scripts de gate ou alterar saída JSON
