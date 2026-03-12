# INDEX de Documentacao (Baseline v4.32)

Este arquivo define a navegacao oficial da documentacao ativa.

## Sync status (2026-03-11 23:35 -0300)

1. Baseline ativo confirmado: `4.32`.
2. Branch operacional: `dev`.
3. Ultimo commit local na sincronizacao deste index: `b63d9133`.
4. Relatorio consolidado do ciclo de build:
   - `docs/BUILD_EXECUTION_AUDIT_20260311.md`
5. Runbook operacional 3x3:
   - `docs/BUILD_3X3_RUNBOOK.md`

## Regras de leitura

1. Baseline ativo de versao: `4.32`.
2. Arquivos em `docs/archive/` sao historicos e nao substituem docs ativos.
3. Em conflito de informacao, prevalece:
   - `AGENTS.md` (raiz)
   - `docs/POLICY_BASELINE_V1_1_FROZEN.md`
   - topo dos docs de controle (`RECOVERY_BACKLOG`, `NEXT_CHAT_MIGRATION`, `AGENTS_HANDOFF_NEXT_CYCLE`)

## Leitura recomendada (ordem)

1. `README.md` (raiz do repositorio)
2. `docs/HISTORICO_RELEASES.md`
3. `docs/COMANDOS_RAPIDOS.md`
4. `docs/GUIA_MIGRACAO_NOVA_INSTALACAO.md`
5. `docs/TROUBLESHOOTING.md`

## Controle operacional

- `docs/RECOVERY_BACKLOG.md`
- `docs/NEXT_CHAT_MIGRATION.md`
- `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- `docs/BUILD_EXECUTION_AUDIT_20260311.md`
- `docs/PENDING_ACTION_MATRIX.md`

### Alertas de curto prazo

1. Debt transversal BLE001 (broad `except Exception`) permanece alto.
2. Referencia canonica da campanha:
   - `docs/RECOVERY_BACKLOG.md` (Priority Note 2026-03-10)
   - `docs/PENDING_ACTION_MATRIX.md` (Update 2026-03-10 near-term stabilization queue)

## Politicas (frozen)

- `docs/POLICY_BASELINE_V1_1_FROZEN.md`
- `docs/POLICY_BASELINE_V1_FROZEN.md`

## Importacao e dados

- `docs/ARQUITETURA_IMPORTACAO.md`
- `docs/IMPORTACAO_ROBUSTA.md`
- `docs/SCHEMA_UNIFICADO_IMPORTACAO.md`
- `docs/DERIVADAS_SYNC_RUNBOOK.md`
- `docs/indicios_importacao.md`
- `docs/TROUBLESHOOTING_IMPORTACAO.md`
- `docs/REGRA_NUMERO_SSA.md`

## GUI e filtros

- `docs/GUI_PYQT6_REGRAS_GERAIS.md`
- `docs/FILTER_TAB_OPTIMIZATIONS.md`
- `docs/GUI_ASYNC_LOADING_GUARDRAILS.md`
- `docs/WORKERS_API_DOCUMENTATION.md`
- `docs/WORKERS_ARCHITECTURE_DIAGRAMS.md`

## Build e distribuicao

- `docs/BUILD_SYSTEM.md`
- `docs/BUILD_MULTIPLATFORM.md`
- `docs/GUIA_DISTRIBUICAO.md`
- `docs/BUILD_PYINSTALLER_GUIA_COMPLETO.md`
- `docs/BUILD_NUITKA_GUIA_COMPLETO.md`
- `docs/BUILD_PYOXIDIZER_GUIA_COMPLETO.md`
- `docs/BUILD_SCRIPTS_COMPARISON.md`
- `docs/BUILD_TOOLING_LESSONS_LEARNED.md`
- `docs/BUILD_EXECUTION_AUDIT_20260311.md`
- `docs/BUILD_3X3_RUNBOOK.md`

## Ferramentas e ambiente

- `docs/TESTING_STRATEGY.md`
- `docs/TESTING_HEADLESS.md`
- `docs/LINTING_MINIMAL.md`
- `docs/OTIMIZACAO_STARTUP.md`
- `docs/MCP_SERVERS_STATUS.md`
- `docs/OPENCODE_CONFIG.md`
- `docs/QWEN_CODE_DELEGATION_CONFIG.md`

## Diagramas tecnicos

- `docs/diagrams/arquitetura_importacao.puml`
- `docs/diagrams/fluxo_sequencia_importacao.puml`
- `docs/diagrams/diagrama_classes.puml`

## Arquivo historico (copias de transicao para auditoria)

Os arquivos abaixo sao snapshots de transicao e nao substituem os docs ativos
de mesmo tema em `docs/`.

- `docs/archive/NEXT_CHAT_MIGRATION_legacy_until_20260309_1735.md`
- `docs/archive/AGENTS_HANDOFF_NEXT_CYCLE_legacy_until_20260309_1735.md`
- `docs/archive/ARQUITETURA_IMPORTACAO_legacy_until_20260309_1901.md`
- `docs/archive/TROUBLESHOOTING_legacy_until_20260309_1901.md`
- `docs/archive/TROUBLESHOOTING_IMPORTACAO_legacy_until_20260309_1901.md`
