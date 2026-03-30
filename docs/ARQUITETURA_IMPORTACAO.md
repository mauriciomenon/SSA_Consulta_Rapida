# Arquitetura de Importacao (Baseline v4.36)

Este documento descreve a arquitetura ativa de importacao no baseline atual.

## Escopo

1. Fluxo de importacao de planilhas para SQLite.
2. Integracao com CLI e GUI sem import automatico no startup.
3. Politica de derivadas: somente full rescan ou acao manual.

## Componentes principais

- `core/app_logic.py`
  - orquestracao de importacao e full rescan.
- `extracao/extractor.py`
  - leitura e normalizacao de planilhas.
- `armazenamento/database_upsert_logic.py`
  - persistencia e merge por `numero_ssa`.
- `armazenamento/database_validation.py`
  - validacoes de dados e regras de consistencia.
- `armazenamento/database_integrity.py`
  - verificacao de integridade e estrutura de schema.

## Fluxo canonico

1. Descoberta dos arquivos de entrada.
2. Extracao e normalizacao de colunas.
3. Validacao de regras de dados.
4. Persistencia no banco alvo.
5. Atualizacao de relatorios de importacao.
6. Em full rescan, sincronizacao de derivadas ao final.

## Contratos operacionais

1. Startup sem import automatico.
2. Full rescan recria DB do zero por politica.
3. Sync de derivadas nao roda no incremental por padrao.
4. Falhas de importacao devem gerar log objetivo, sem suppress silencioso.

## Fonte de verdade para operacao

- Estado operacional e decisoes de ciclo:
  - `docs/RECOVERY_BACKLOG.md`
  - `docs/NEXT_CHAT_MIGRATION.md`
  - `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`

## Historico tecnico detalhado

O conteudo detalhado legado desta arquitetura foi arquivado em:

- `docs/archive/ARQUITETURA_IMPORTACAO_legacy_until_20260309_1901.md`

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->

