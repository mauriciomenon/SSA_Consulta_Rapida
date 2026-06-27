# Changelog

All notable changes to this project are documented in this file.

## [Unreleased] - 2026-06-27

### Changed
- Local top on `dev` after baseline `4.43`:
  - Runtime metadata, packaging test expectations and active documentation now point to `4.43`.
  - Persistent saved filters materialize visible advanced filter selections before deduplication.
  - Deleted Qt `FilterWorker` shutdown is treated as benign cleanup instead of a warning.
  - Previous local-top notes after `4.37` remain historical context below.
  - SSA detail popup keeps lower derivadas/relacionadas area with more usable height.
  - fallback graph without DB now includes the direct parent, avoiding incomplete local hierarchy rendering.
  - local detail navigation keeps `ssa:` clicks in the details context without rewriting global search text.
- GUI status contract split:
  - `filtered_status_label` now shows only `Status: X de Y SSAs`.
  - `status_label` now shows search and zero-result notices.
- Windows column widths synchronized across runtime defaults and versioned GUI preferences.
- GUI filter tests updated to use a realistic 50-row sanitized fixture and assert the split status behavior.
- Derivadas sync agora roda por padrao ao final de qualquer adicao valida de SSAs:
  - importacao diff
  - reescaneamento completo
  - importacao explicita por arquivo
- GUI agora recarrega os dados automaticamente apos alteracao valida do banco em importacao ou reescaneamento.

### Validation
- Runtime visual checks executed with programmatic PyQt rendering:
  - popup details
  - derivadas/relacionadas graph
  - lower details panel
- Focused local validation recently green on affected slices:
  - `py_compile`
  - `ruff`
  - `ty`
  - focused `pytest` on GUI detail navigation, popup graph, and import-trigger contracts

## [v4.43] - 2026-06-27

### Changed
- Promoted local active baseline to `4.43`.
- Synchronized runtime metadata in `VERSION`, `config/version.json`, `pyproject.toml` and `uv.lock`.
- Aligned active docs and packaging-related tests to versioned names `v4.43`.
- Reserved local tag `v4.43` before functional GUI/filter/cache stabilization slices.

## [v4.42] - 2026-06-11

### Changed
- Promoted local active baseline to `4.42`.
- Synchronized runtime metadata in `VERSION`, `config/version.json` and `pyproject.toml`.
- Aligned active docs and packaging-related tests to versioned names `v4.42`.
- Saved filters now capture pending advanced UI selections before duplicate detection.
- Filter worker shutdown no longer logs benign deleted Qt wrapper errors as warnings.

## [v4.37] - 2026-04-01

### Changed
- Promoted local active baseline to `4.37` while preserving `v4.36` as the latest published GitHub tag.
- Hardened GUI state contracts around:
  - general search ownership
  - header reorder/sort/resize persistence
  - details preservation across refreshes
  - derivadas navigation and details rendering
- Consolidated derivadas/details popup with graph export, tree view, platform width handling, and active-screen clamping.
- Extended import/storage hardening:
  - anti-downgrade protection for `situacao` on same-date updates
  - explicit single-file import path
  - DB repair/recreate flows for invalid or incomplete databases
- Aligned active docs to a single current-truth model across continuity and handoff files.

### Notes
- `4.37` is the active local baseline in runtime and docs.
- `v4.36` remains the latest published GitHub tag at this time.

## [v4.36] - 2026-04-01

### Changed
- Centralized `numero_ssa` storage normalization and aligned simple insert/storage sanitization.
- Stabilized simplified filter contracts and derivadas alias preflight.
- Closed a focused `pytest`/`ty`/`bandit` min-fix slice to support the tag transition.
- Prepared the 4.36 handoff/documentation transition.

## [v4.35] - 2026-03-24

### Changed
- Closed nullable/filter/display regressions tied to full rescan and DB readback.
- Hardened async jump-to-SSA and details rendering behavior in the GUI.
- Normalized related SSA identifiers during import and preserved canonical text storage.
- Reduced local noise from `docs_entrada` and cleaned explicit DB option packaging for local operation.

## [v4.29] - 2026-03-02

### Changed
- Release `4.29` com estabilizacao de tema/legibilidade na GUI:
  - padronizacao de popup/menu/checkbox com roles de tema;
  - texto de selecao em botoes de multiselect mostra conteudo completo quando cabe;
  - truncamento por largura util, sem corte fixo arbitrario;
  - ajustes de robustez para evitar acesso a widget Qt invalido em relayout.
- Metadados de versao sincronizados para `4.29` em `VERSION` e `config/version.json`.

## [v4.27] - 2026-03-01

### Changed
- Runtime/documentation moved to uv-first usage with explicit command priority:
  - `uv run --python 3.13 ...` as first option.
  - fallback order documented: 3.12 -> 3.11 -> 3.10.
- `requires-python` updated to `>=3.10` to keep compatibility without dropping 3.13 priority.
- `dev_env/bootstrap.sh` and `dev_env/bootstrap.ps1` now prefer 3.13 and fallback to 3.12/3.11/3.10.
- `gui/gui_ssa.py` fallback for open folder now checks executable availability (`explorer`, `open`, `xdg-open`) before spawning.
- `interface/cli_enhancement_manager.py` applies POSIX-specific chmod/fsync steps only on POSIX.

### Validation
- Multi-version isolated matrix completed with uv envs:
  - Python 3.10.18: pass
  - Python 3.11.14: pass
  - Python 3.12.11: pass
  - Python 3.13.12: pass
- Focused checks per version:
  - `py_compile`, `ruff`, `ty`
  - `pytest -q tests/test_open_docs_folder_nonblocking.py tests/test_cli_enhancement_manager_lock_usage.py tests/test_cli_enhancement_manager_atomic_save.py`

## [Historical Unreleased] - 2025-11-10

### Fixed
- **Missing imports in mixins**: Fixed NameError when accessing format_search_display and GUI_MAIN_PREFERENCES in gui/mixins/filter_gui_ssa_mixin.py
- **Desynchronized progress callbacks**: Synchronized events between core/app_logic.py and RescanWorker (file_start, file_success, file_error)
- **Record counting**: _import_single_file now returns actual number of processed records
- **Single-instance lock**: Removed buggy mechanism via TCP socket that caused hangs

### Changed
- main.py: Removed single-instance check code
- core/app_logic.py: Function _import_single_file returns tuple[bool, int] instead of just bool
- GUI allows multiple simultaneous instances (real lock is in SQLite)

### Added
- **Verification script**: verify_integrity.py for general system validation
- **Specialized script**: verify_mixin_imports.py to detect missing imports in mixins
- **Documentation**: docs/VERIFICACAO_INTEGRIDADE.md with complete technical details

### Technical Details
- Callbacks now report: start (file_start), success with count (file_success), and errors (file_error)
- Import shows real-time progress in GUI
- SQLite uses WAL mode + busy timeout for concurrency control

---

## [v4.10.0] - 2025-11-10
Released: https://github.com/mauriciomenon/SSA_Consulta_Rapida/releases/tag/v4.10.0

### Contexto historico
Serie 4.0 apresentou problemas persistentes em dois eixos principais: filtros e temas. Em filtros houve interpretacao incorreta de conectivos visuais, divergencia entre GUI e CLI em casos com OU encadeado e regressao em cache que permitia exibicao parcial sem aplicacao correta de exclusoes com prefixo !. Em temas houve inconsistencias na aplicacao de papeis de cor para quadros resumo, indicadores laterais e tags de filtros salvos causando contraste irregular e legibilidade reduzida em alguns sistemas.

### Correcoes
- Unificacao de parsing de conectivos OU entre GUI CLI e streamlit sem substituicao visual ambigua
- Remocao de normalizacao tardia que gerava estado intermediario incoerente nos testes de filtros
- Ajuste de cache de filtros garantindo invalidacao quando conectivos OU ou negativos sao adicionados ou removidos
- Revisao de mapeamento de papeis de tema para quadros indicadores e tags garantindo aplicacao de chave unica centralizada
- Inclusao de chaves de tema ausentes herdadas da serie 4.0 para impedir fallback silencioso

### Impacto
- Fluxo de busca retorna resultados consistentes entre interfaces
- Filtros negativos nao sao ignorados em combinacoes com OU
- Temas aplicam cores previsiveis sem variar entre plataformas
- Registro explicito do historico evita reintroducao das falhas

### Notas
- Sem alteracao de schema de banco
- Sem mudanca em formatos de exportacao
- Versao marca encerramento das falhas iniciadas na serie 4.0

---

## [v4.0.3] - 2025-10-09
Released: https://github.com/mauriciomenon/SSA_Consulta_Rapida/releases/tag/v4.0.3

### Highlights
- Theming: all GUI accents (frames, indicators, tag buttons, macOS contrast) now consume centralized theme roles, with new role entries for summary frames and indicator text across every theme.
- UX: global search box normalizes visual connectors, so inputs like `A || B` are displayed as `A OU B`, matching per-column behaviour and keeping the tests green.
- Consistency: summary badges, saved-filter tags, and column-filter widgets share the same palette-driven styling on both Windows and macOS.

### Notes
- No data or schema changes.
- New theme keys (`summary_*`, `indicator_text_color`) default gracefully; custom themes should extend `utils/themes.py` accordingly.

---

## [v4.0.1] - 2025-10-03
Released: https://github.com/mauriciomenon/SSA_Consulta_Rapida/releases/tag/v4.0.1

### Highlights
- GUI: added "[+ OU]" per-column UI button to compose OR conditions in a single column (UI-only; storage unchanged).
- Robustness: explicit cleanup of QThreads to eliminate thread-destruction warnings.
- Documentation: `docs/HISTORICO_ULTIMOS_50_COMMITS.md` added with a navigable index and appendices.

### Notes
- No database schema changes.
- No filter syntax changes.

---

For the full technical changelog and implementation details, see `docs_saida/CHANGELOG_IMPLEMENTACOES.md` and `docs/HISTORICO_ULTIMOS_50_COMMITS.md`.

## Atualizacao 2026-03-01 (ciclo gui-tema-import)
- Corrigido tema dos menus de selecao para herdar cores do tema ativo (sem fallback escuro fixo).
- Reduzido tamanho efetivo dos botoes Aplicar/Limpar dos filtros avancados.
- Corrigido comportamento de largura de popup dos seletores para evitar expansao excessiva.
- Reforcado import otimizado: deduplicacao por numero_ssa e falha explicita em lookup SQL parcial.
- Corrigidos comentarios recentes de review (scripts/tests/docs) e removidos emojis em arquivos versionados.

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->
