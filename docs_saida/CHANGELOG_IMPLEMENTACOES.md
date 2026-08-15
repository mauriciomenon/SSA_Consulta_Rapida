# CHANGELOG DE IMPLEMENTACOES

## 2026-03-02 - Release v4.29 (tema geral + legibilidade)
- Baseline de release patch atualizado:
  - `VERSION` para `4.29`
  - `config/version.json` para baseline `v4.29`
- GUI de filtros/tabela com consistencia de tema por regra geral:
  - popups/menus/checks amarrados a roles de tema, com reducao de fallback visual ad-hoc;
  - resumo de multiselect exibe texto completo quando ha espaco e trunca pelo ultimo caractere util;
  - ajustes de robustez em relayout para evitar acesso a widget Qt invalido.

## 2026-03-01 - Release v4.27 (uv-first + python compatibility)
- Baseline de release atualizado:
  - `VERSION` para `4.27`
  - `config/version.json` para baseline `v4.27`
- Runtime/docs alinhados para padrao uv-first:
  - comando principal em docs: `uv run --python 3.13 ...`
  - fallback documentado: `3.12 -> 3.11 -> 3.10`
  - `requirements*.txt` mantidos para compatibilidade (nao como caminho principal)
- Matriz multi-versao validada com ambientes uv isolados:
  - 3.10.18: pass
  - 3.11.14: pass
  - 3.12.11: pass
  - 3.13.12: pass

## 2026-02-28 - Release v4.27 (Pre-PR release alignment)
- Alinhamento de metadados de release para remover drift entre docs e arquivos de versao:
  - `VERSION` para `4.27`
  - `config/version.json` para baseline `v4.27`
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

## Atualizacao 2026-03-01 (ciclo gui-tema-import)
- Corrigido tema dos menus de selecao para herdar cores do tema ativo (sem fallback escuro fixo).
- Reduzido tamanho efetivo dos botoes Aplicar/Limpar dos filtros avancados.
- Corrigido comportamento de largura de popup dos seletores para evitar expansao excessiva.
- Reforcado import otimizado: deduplicacao por numero_ssa e falha explicita em lookup SQL parcial.
- Corrigidos comentarios recentes de review (scripts/tests/docs) e removidos emojis em arquivos versionados.

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->

