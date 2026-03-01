# CHANGELOG DE IMPLEMENTACOES

## 2026-02-28 - Release v4.26.0 (Pre-PR release alignment)
- Alinhamento de metadados de release para remover drift entre docs e arquivos de versao:
  - `VERSION` para `4.26.0`
  - `config/version.json` para baseline `v4.26.0`
- Sincronizacao de docs de release e continuidade:
  - `README.md`
  - `docs/HISTORICO_RELEASES.md`
  - `docs/NEXT_CHAT_MIGRATION.md`
  - `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
  - `docs/RECOVERY_BACKLOG.md`
- Escopo de seguranca:
  - sem mudanca em logica streamlit.
  - sem mudanca em hardening de runtime.

## 2026-02-28 - Release v4.25.0 (Sprint 25 graves closure)
- Integracao do pacote de hardening antes preservado em stash:
  - SQL guard em `armazenamento/database_optimized.py`
  - cancelamento e guardrails de extracao em `core/app_logic.py`
  - validacao de path/mapping em `interface/command_handlers.py`
- Regressoes focadas adicionadas para command handlers, importer e wrappers.
- Sync de docs de handoff e backlog para continuidade do ciclo.

## 2026-02-28 - Release v4.24.1 (Streamlit filtros estaveis)
- Expansao de filtros selecionaveis e dica de busca no streamlit.
- Ajustes de usabilidade da tabela e compactacao de filtros principais.
- Testes streamlit focados atualizados para cache e filtros.

## 2025-08-14 - Ajustes de exibição e filtros críticos
- Revisado `column_priority.json` para estabilizar `essential` e `always_visible`, evitando regressao de colunas em dashboards CLI/GUI.
- GUI recebeu correcoes nos tooltips de filtros, mantendo paridade textual com o CLI e reduzindo duvida em conectivos OU/OR.
- Atualizacao do README enfatizando politicas de remocao de artefatos de IA e links diretos para o changelog tecnico.

## 2025-07-29 - Preparacao release 4.12
- Sincronizacao dos metadados de versao (arquivo `VERSION` + `config/version.json`) antes do congelamento de build.
- Conferencia de scripts de logging para garantir que handlers continuem emitindo metricas de desempenho em execucoes GUI/CLI.
- Revisao das prioridades de colunas para exportacao, validando novamente as chaves `short_labels` e `fixed_widths` usadas no CLI.
