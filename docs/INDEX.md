# INDEX de Documentacao (Baseline v4.44 local / v4.36 published)

Este arquivo define a navegacao oficial da documentacao ativa.

## Sync status (2026-04-15 21:50 -0300)

1. Baseline ativo confirmado: `4.44`.
2. Branch operacional: `dev`.
3. Release/tag publicada relevante: `v4.36`.
4. Estado atual do branch:
   - `HEAD` local esta 1 commit a frente de `origin/dev`
   - PR remoto ainda aponta para `fb068228`
5. Ultimos slices funcionais relevantes nesta frente:
   - `3fa1b38d` `STABILITY_PATCH: version gui preferences reference file and width precedence`
   - slice atual desta rodada: isolamento e restauracao do estado global de lifecycle em `tests/test_gui_filter_logic.py`
6. O contrato de preferencias GUI agora precisa ser lido assim:
   - se faltar `config/gui_main_preferences.json` ou mudar `SSA_CONFIG_DIR`, o runtime usa os defaults em memoria do codigo
   - largura persistida valida vence a largura automatica
   - fallback local da tabela e baseline automatico partem de `gui/gui_config.py`
   - `config/gui_main_preferences.json` e o arquivo efetivo tracked de runtime; o `.example` documenta o padrao; codigo define a base
   - reorder e hide/show de colunas persistem no mesmo arquivo local
   - o header da GUI agora usa matriz explicita `short/medium/long` por coluna e escolhe a maior variante que cabe na largura real, com reserva para `[f] `
   - a CLI continua fora do contrato de preferencias da GUI, mas segue usando `display_map`, `short_labels`, `fixed_widths` e alternancia `short/full`
   - `core/handler_base.py:197` permanece apenas como renderer paralelo documentado, fora do caminho principal `main.py -> interface/cli.py -> interface/table_printer.py`
7. PR operacional atual:
   - `#47` `dev -> main`
   - `mergeStateStatus=UNSTABLE`
8. Checks remotos relevantes no momento:
   - `DeepSource: Python` -> status externo ruidoso; tratar como warning operacional
   - `code/snyk (mauriciomenon)` -> fail por limite/conta; tratar como warning operacional
   - `security/snyk (mauriciomenon)` -> fail por limite/conta; tratar como warning operacional
   - `dev` e `main` sem branch protection obrigando esses checks neste host
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
16. Widths por sistema operacional da GUI:
   - `docs/COLUMN_WIDTHS_BY_PLATFORM.md`
17. Estado atual do harness de testes GUI:
   - `tests/test_gui_filter_logic.py` agora limpa e restaura globais de workers aposentados por teste
   - a correcao fecha a pendencia media confirmada de vazamento de lifecycle entre casos

## Regras de leitura

1. Baseline ativo de versao: `4.44`.
2. Em conflito de informacao, prevalece:
   - `AGENTS.md` (raiz)
   - `docs/POLICY_BASELINE_V1_1_FROZEN.md`
   - `README.md` e este indice

## Leitura recomendada (ordem)

1. `README.md` (raiz do repositorio)
2. `docs/HISTORICO_RELEASES.md`
3. `docs/COMANDOS_RAPIDOS.md`
4. `docs/GUIA_MIGRACAO_NOVA_INSTALACAO.md`
5. `docs/TROUBLESHOOTING.md`

## Controle operacional

- `docs/MAC_CONTINUATION_HANDOFF_20260329.md`
- `docs/BUILD_EXECUTION_AUDIT_20260311.md`

### Alertas de curto prazo

1. Debt transversal BLE001 (broad `except Exception`) permanece alto.
2. Pendencias novas devem ser tratadas no PR/conversa, sem publicar backlog interno no repositorio.

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

- `docs/GUI_STATE_CONTRACT_POSTMORTEM_20260409.md`
- `docs/GUI_MAIN_PREFERENCES_STRUCTURE.md`
- `docs/COLUMN_WIDTHS_BY_PLATFORM.md`
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
## Diagramas tecnicos

- `docs/diagrams/arquitetura_importacao.puml`
- `docs/diagrams/fluxo_sequencia_importacao.puml`
- `docs/diagrams/diagrama_classes.puml`

<!-- DOC_SYNC_MAC: 2026-03-30 contract-aligned -->
