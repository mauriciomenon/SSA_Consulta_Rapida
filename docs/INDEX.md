# INDEX de Documentacao (Baseline v4.36)

Este arquivo define a navegacao oficial da documentacao ativa.

## Sync status (2026-04-07 00:30 -0300)

1. Baseline ativo confirmado: `4.36`.
2. Branch operacional: `dev`.
3. Release/tag publicada relevante: `v4.36`.
4. `HEAD == origin/dev` confirmado no fim do slice atual.
5. Ultimos slices funcionais relevantes nesta frente:
   - `3fa1b38d` `STABILITY_PATCH: version gui preferences reference file and width precedence`
   - slice atual desta rodada: alinhamento do baseline automatico do width manager ao contrato canonico, sem reabrir `DEFAULT_COLUMN_WIDTHS`
6. O contrato de preferencias GUI agora precisa ser lido assim:
   - se faltar `config/gui_main_preferences.json` ou mudar `SSA_CONFIG_DIR`, o runtime usa os defaults em memoria do codigo
   - largura persistida valida vence a largura automatica
   - fallback local da tabela e baseline automatico partem de `gui/gui_config.py`
   - arquivo local tem a ultima palavra; o `.example` documenta o padrao; codigo define a base
   - reorder e hide/show de colunas persistem no mesmo arquivo local
   - o header da tabela usa alias fixo por coluna; nao ha algoritmo dinamico de label curta/media/longa hoje
   - a CLI continua fora do contrato de labels/visibilidade da GUI
7. PR operacional atual:
   - `#46` `dev -> main`
   - `mergeStateStatus=UNSTABLE`
8. Checks remotos relevantes no momento:
   - `DeepSource: Python` -> fail
   - `code/snyk (mauriciomenon)` -> fail por limite da ferramenta
9. `kluster` esta disponivel neste host:
   - `/Users/menon/.kluster/cli/bin/kluster`
10. Sprint GUI desta frente ja foi aterrado no runtime:
   - `Abrir SAM`
   - status `filtrado/total`
   - `#` abrindo SAM externo
   - `situacao` expandida no detalhe
   - copia por duplo clique do numero da SSA
   - derivadas em arvore textual e detalhe mais largo
   - `load_other_database()` fora da UI thread em runtime normal
11. Relatorio consolidado do ciclo de build:
   - `docs/BUILD_EXECUTION_AUDIT_20260311.md`
12. Runbook operacional 3x3:
   - `docs/BUILD_3X3_RUNBOOK.md`
13. Contrato de upsert/update por SSA alinhado nos docs vivos:
   - `docs/ARCH_DB_UPSERT.md`
   - `docs/ARQUITETURA_IMPORTACAO.md`
   - `docs/TROUBLESHOOTING_IMPORTACAO.md`
   - `docs/FORENSIC_UPDATE_CRITERIA_SSA_20260329.md`
14. Handoff host-agnostic para continuidade no macOS:
   - `docs/MAC_CONTINUATION_HANDOFF_20260329.md`
15. Estrutura canonica de preferencias da GUI:
   - `docs/GUI_MAIN_PREFERENCES_STRUCTURE.md`

## Regras de leitura

1. Baseline ativo de versao: `4.36`.
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
- `docs/MAC_CONTINUATION_HANDOFF_20260329.md`
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

- `docs/GUI_MAIN_PREFERENCES_STRUCTURE.md`
- `docs/GUI_PYQT6_REGRAS_GERAIS.md`
- `docs/FILTER_TAB_OPTIMIZATIONS.md`
- `docs/GUI_ASYNC_LOADING_GUARDRAILS.md`
- `docs/WORKERS_API_DOCUMENTATION.md`
- `docs/WORKERS_ARCHITECTURE_DIAGRAMS.md`
- `docs/archive/LEGACY_DOCS_REORG_STUDY_20260327.md`

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
- `docs/archive/LEGACY_DOCS_REORG_STUDY_20260327.md`

<!-- DOC_SYNC_MAC: 2026-03-30 contract-aligned -->
