# Analise Profunda GUI (v4.36)

Documento de referencia ativa para estado tecnico da GUI PyQt6.
Escopo: diagnostico objetivo, riscos reais e plano minimo reversivel.

## Resumo executivo
- O modulo `gui/gui_ssa.py` permanece como facade publica e ponto de integracao.
- A estrutura modular em `gui/ssa/*` esta em producao e cobre tema, workers, filtros, tabela e detalhes.
- O risco principal atual nao e sintaxe, e sim manutencao em modulo grande com historico longo.
- Politica ativa: patch minimo, sem mudanca de layout sem pedido explicito, validacao por gates.

## Estado atual confirmado
- Release baseline: `4.36`.
- Branch de trabalho: `dev`.
- Fluxo de execucao recomendado:
  - `uv run --python 3.13 python main.py --gui`
  - fallback: `3.12 -> 3.11 -> 3.10`
- Compatibilidade matrix ja validada no ciclo atual em 3.10/3.11/3.12/3.13.

## Riscos tecnicos relevantes
1. Alta acoplacao historica em `gui/gui_ssa.py`:
   - facade concentra estado e orquestracao de varios dominios.
   - risco de regressao indireta ao tocar handlers centrais.
2. Concorrencia de workers:
   - manter o contrato de retencao/prune para evitar race em encerramento e rescan.
3. Filtros avancados:
   - preservar ordem e sincronizacao de checks/multiselect para evitar divergir da tabela.
4. Contrato de tema:
   - alteracoes devem manter paridade entre papeis de tema e widgets.

## Controles obrigatorios por slice GUI
1. Rodar kluster no escopo alterado.
2. Rodar gates minimos:
   - `uv run --python 3.13 python -m py_compile <arquivos>`
   - `uv run ruff check <arquivos>`
   - `uv run ty check <arquivos>`
   - `uv run pytest -q <focados>`
3. Nao aceitar merge com erro silencioso de runtime.
4. Commit atomico com rollback simples.

## Referencias complementares
- `GUI_SSA_REFACTOR_NOTES.md`
- `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- `docs/NEXT_CHAT_MIGRATION.md`
- `docs/RECOVERY_BACKLOG.md`
- `docs/PENDING_ACTION_MATRIX.md`

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->

