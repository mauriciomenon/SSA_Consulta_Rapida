# CHANGELOG_IMPLEMENTACOES

Arquivo legado mantido para compatibilidade com testes automatizados. O histórico completo e detalhado permanece em `docs_saida/CHANGELOG_IMPLEMENTACOES.md`.

## 2025-08-15
- Removida GUI PoC `gui/gui_ssa_poc.py` e testes correlatos para reduzir ruído de manutenção.
- Estruturado novo conjunto de quality gates iniciais (validação de configs / smoke CLI rascunho).

## 2025-08-28
- Refatoração do pipeline de importação e normalização de `numero_ssa`.
- Introdução de testes de upsert garantindo não regressão de datas mais novas.

## 2025-09-05
- Adicionado modo de filtragem síncrona (`SSA_SYNC_FILTER`) para estabilizar testes GUI evitando race com `QThread`.
- Simplificação de layout de filtros duplicados na janela principal.

## 2025-09-10
- Ajustes de compatibilidade retroativa nas funções de banco para aceitar tanto `db_path` quanto conexões SQLite abertas.
- Melhoria na lógica de comparação de datas no upsert (não sobrescrever com registro mais antigo).

## 2025-09-12
- Revisão dos mapeamentos de exibição de colunas e restauração de acentuação (`Número SSA` / fallback sem acento para caminhos legados).
- Correções de assinatura de slots de menu de contexto (ex.: `copy_cell_value`).

Para histórico completo e decisões arquiteturais ver: `docs/HISTORICO_RELEASES.md` e `docs_saida/CHANGELOG_IMPLEMENTACOES.md`.
