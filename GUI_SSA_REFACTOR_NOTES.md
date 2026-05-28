# GUI SSA Refactor Notes (v4.27)

Status: documento ativo de referencia tecnica para manutencao/reorganizacao da GUI.
Escopo: registrar contratos do facade, limites de refatoracao e ordem segura de mudancas.

## Objetivo
Manter `gui/gui_ssa.py` estavel como facade publica enquanto a logica continua modular em `gui/ssa/*`, sem regressao de comportamento e sem mudanca de layout nao solicitada.

## Contrato de arquitetura atual
1. `gui/gui_ssa.py`:
   - facade e integracao de estado da janela principal.
   - ponto de entrada de sinais, tabs e roteamento para modulos `gui/ssa`.
2. `gui/ssa/gui_theme.py`:
   - tema, catalogo e aplicacao de estilos.
3. `gui/ssa/gui_workers.py`:
   - ciclo de vida de workers e callbacks de carga/rescan.
4. `gui/ssa/gui_filters_advanced_ui.py` + `gui/ssa/gui_filters_advanced_logic.py`:
   - montagem de UI de filtros avancados e aplicacao de filtros.
5. `gui/ssa/gui_table.py`:
   - render de tabela e largura/paginacao.
6. `gui/ssa/gui_details.py`:
   - detalhes e highlight.

## Regra de ouro para refatoracao
1. Sem alterar layout/posicao sem pedido explicito.
2. Sem refatoracao transversal ampla.
3. Cada slice deve ser reversivel por commit atomico.
4. Evitar try/except silencioso novo.

## Ordem segura para mudancas futuras
1. Diagnostico e evidencia (arquivo/linha/risco).
2. Patch minimo no modulo alvo.
3. Kluster no escopo alterado.
4. Gates:
   - `uv run --python 3.13 python -m py_compile <arquivos>`
   - `uv run ruff check <arquivos>`
   - `uv run ty check <arquivos>`
   - `uv run pytest -q <focados>`
5. Commit e push.

## Itens de atencao
1. Workers:
   - nao quebrar contratos de prune/retencao.
2. Filtros avancados:
   - preservar sincronizacao de checks, chips e estado de tabela.
3. Tema:
   - manter consistencia de papeis de cor em widgets e tabela.
4. Streamlit:
   - e sidequest; manter concentrado em um arquivo, sem invadir GUI PyQt6.

## Referencias
- `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- `docs/NEXT_CHAT_MIGRATION.md`
- `docs/RECOVERY_BACKLOG.md`
- `docs/PENDING_ACTION_MATRIX.md`

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->
