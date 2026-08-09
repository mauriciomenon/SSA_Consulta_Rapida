# INDEX de Documentacao (Release v4.47)

Este arquivo define a navegacao oficial da documentacao ativa.

## Sync status (2026-08-09)

1. Release estavel confirmada: `4.47`.
2. Branch operacional: `dev`.
3. Release/tag atual: `v4.47`.
4. Tag anterior: `v4.46`.
5. Estado Git atual:
   - mapa canonico: `origin` = GitLab, `bitbucket` = Bitbucket, `gh` = GitHub.
   - `dev` deve permanecer publicado em `origin/dev` e `bitbucket/dev`; `git pull` padrao usa `origin/dev`.
6. Estado remoto:
   - GitLab e Bitbucket estao operacionais para fetch, pull e push.
   - HTTP 403 por conta suspensa afeta somente `gh`; PR, checks, tag e release no GitHub continuam bloqueados.
7. Slices relevantes da release `v4.47`:
   - `0f164b3a` `STABILITY_PATCH: cycle quick status filter states`
   - `f7f71a48` `STABILITY_PATCH: harden Windows portability and scripts`
   - `7200ce33` `UI_FIX: show ellipsis for multiple quick sectors`
8. Historico anterior desde `v4.43`:
   - `445f1d25` `STABILITY_PATCH: fix validation gates for v4.44 baseline`
   - `acc299f8` `STABILITY_PATCH: fix ty validation gate`
   - `4ae43f05` `DOC_SYNC: promote local baseline to 4.44`
   - `75c30f2f` `DOC_SYNC: close filter hardening audit statuses`
   - `7eab54b5` `DOC_SYNC: align v4.44 operational status`
   - `54bcbc00` `STABILITY_PATCH: show commit ISO date in about dialog`
   - `2a19d876` `DOC_SYNC: align active docs to v4.44`
   - `bd76ace3` `STABILITY_PATCH: replace runtime select star queries`
   - `c3874e49` `DOC_SYNC: record P2 runtime cleanup status`
   - `bdad722c` `STABILITY_PATCH: harden Windows build wrapper cleanup`
   - `63631e72` `STABILITY_PATCH: harden release_windows.ps1 pre-zip workspace`
9. Estado validado local:
   - `ruff check .`, `ty check` e `py_compile`: OK
   - contratos focados de release e multiplataforma: `122 passed, 6 skipped`
   - suite completa: `2551 passed, 16 skipped`; a unica falha era uma expectativa visual antiga
   - modulo corrigido revalidado por inteiro: `550 passed, 1 skipped`
   - `pip-audit`: nenhuma vulnerabilidade conhecida apos os patches minimos de `gitpython`, `python-multipart`, `setuptools` e `starlette`
   - `semgrep`: 0 achados bloqueantes; `bandit`: 0 achados medios ou altos
10. Pendencias imediatas:
   - nenhuma pendencia funcional bloqueante conhecida para `v4.47`
   - espelhamento no GitHub permanece bloqueado por HTTP 403; GitLab e Bitbucket nao sao afetados
   - publicacao so e valida quando o build limpo e os smokes reais Windows estiverem registrados no relatorio JSON

## Snapshot historico de abril/GUI

O bloco abaixo e contexto historico da frente GUI/preferencias de abril de 2026. Nao representa o estado remoto ou PR atual.

1. Baseline historico da frente: `4.44` apos promocao local.
2. Estado historico do branch naquela frente:
   - `HEAD` local esta 1 commit a frente de `origin/dev`
   - PR remoto ainda aponta para `fb068228`
3. Ultimos slices funcionais relevantes naquela frente:
   - `3fa1b38d` `STABILITY_PATCH: version gui preferences reference file and width precedence`
   - slice atual desta rodada: isolamento e restauracao do estado global de lifecycle em `tests/test_gui_filter_logic.py`
4. O contrato de preferencias GUI daquela frente deve ser lido assim:
   - se faltar `config/gui_main_preferences.json` ou mudar `SSA_CONFIG_DIR`, o runtime usa os defaults em memoria do codigo
   - largura persistida valida vence a largura automatica
   - fallback local da tabela e baseline automatico partem de `gui/gui_config.py`
   - `config/gui_main_preferences.json` e o arquivo efetivo tracked de runtime; o `.example` documenta o padrao; codigo define a base
   - reorder e hide/show de colunas persistem no mesmo arquivo local
   - o header da GUI agora usa matriz explicita `short/medium/long` por coluna e escolhe a maior variante que cabe na largura real, com reserva para `[f] `
   - a CLI continua fora do contrato de preferencias da GUI, mas segue usando `display_map`, `short_labels`, `fixed_widths` e alternancia `short/full`
   - `core/handler_base.py:197` permanece apenas como renderer paralelo documentado, fora do caminho principal `main.py -> interface/cli.py -> interface/table_printer.py`
5. PR operacional historico:
   - `#47` `dev -> main`
   - `mergeStateStatus=UNSTABLE`
6. Checks remotos historicos daquela frente:
   - `DeepSource: Python` -> status externo ruidoso; tratar como warning operacional
   - `code/snyk (mauriciomenon)` -> fail por limite/conta; tratar como warning operacional
   - `security/snyk (mauriciomenon)` -> fail por limite/conta; tratar como warning operacional
   - `dev` e `main` sem branch protection obrigando esses checks neste host
7. `kluster` estava disponivel neste host:
   - `/Users/menon/.kluster/cli/bin/kluster`
8. Sprint GUI daquela frente foi aterrado no runtime:
   - `Abrir SAM`
   - status `filtrado/total`
   - `#` abrindo SAM externo
   - `situacao` expandida no detalhe
   - copia por duplo clique do numero da SSA
   - derivadas em arvore textual e detalhe mais largo
   - `load_other_database()` fora da UI thread em runtime normal
9. Relatorio consolidado do ciclo de build:
   - `docs/BUILD_EXECUTION_AUDIT_20260311.md`
10. Runbook operacional 3x3:
   - `docs/BUILD_3X3_RUNBOOK.md`
11. Contrato de upsert/update por SSA alinhado nos docs vivos:
   - `docs/ARCH_DB_UPSERT.md`
   - `docs/ARQUITETURA_IMPORTACAO.md`
   - `docs/TROUBLESHOOTING_IMPORTACAO.md`
   - `docs/FORENSIC_UPDATE_CRITERIA_SSA_20260329.md`
12. Handoff host-agnostic para continuidade no macOS:
   - `docs/MAC_CONTINUATION_HANDOFF_20260329.md`
13. Estrutura canonica de preferencias da GUI:
   - `docs/GUI_MAIN_PREFERENCES_STRUCTURE.md`
14. Widths por sistema operacional da GUI:
   - `docs/COLUMN_WIDTHS_BY_PLATFORM.md`
15. Estado historico do harness de testes GUI:
   - `tests/test_gui_filter_logic.py` agora limpa e restaura globais de workers aposentados por teste
   - a correcao fecha a pendencia media confirmada de vazamento de lifecycle entre casos

## Regras de leitura

1. Release ativa: `4.47`. Tag anterior: `v4.46`.
2. Em conflito de informacao, prevalece:
   - `AGENTS.md` (raiz)
   - `docs/POLICY_BASELINE_V1_1_FROZEN.md`
   - `README.md` e este indice

## Leitura recomendada (ordem)

1. `README.md` (raiz do repositorio)
2. `docs/RELEASE_NOTES_v4.47.md`
3. `docs/HISTORICO_RELEASES.md`
4. `docs/COMANDOS_RAPIDOS.md`
5. `docs/GUIA_MIGRACAO_NOVA_INSTALACAO.md`
6. `docs/TROUBLESHOOTING.md`

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
