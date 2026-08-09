# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

## [v4.47] - 2026-08-09

### Changed
- Quick executor-sector selector now shows `...` when more than one sector is active.
- Existing active, column and advanced executor-sector filter synchronization remains unchanged.
- Runtime and package metadata now identify stable release `4.47`.

### Notes
- No database schema, application filter-operator or layout change.
- This release consolidates the stable fixes introduced after `v4.45.2`, including the `v4.46` status-filter cycle.

### Security
- Updated locked `gitpython` from `3.1.57` to `3.1.58`, `python-multipart` from `0.0.28` to `0.0.31`, `setuptools` from `82.0.1` to `83.0.0` and `starlette` from `1.0.1` to `1.3.1`.
- These are the minimum versions that clear the advisories reported by `pip-audit` in build, development and web dependency paths.

### Validation
- Full candidate suite completed with 2551 passed and 16 skipped; its only failure was a stale visual expectation, then the full affected GUI module passed with 550 passed and 1 skipped.
- Release contracts, static checks and dependency audit passed before the clean Windows build gate.

## [v4.46] - 2026-08-09

### Changed
- Quick SSA status buttons cycle through included, excluded (`!STATUS`) and neutral states.
- Status-button state remains synchronized with active and advanced filter views.
- Windows activation and test scripts received native path and portability hardening.

### Dependency update cycle - 2026-07-15
- Created local checkpoint tag `v4.45.1` at commit `d8c4033c6828f1ecde05f4f3140f137ee43d496f` before the dependency update slice. The tag is not published.
- Completed the dependency audit with `uv tree --outdated`, `pip-audit`, Safety, `pip check`, and `uv lock --check`.
- Current `uv.lock` contains PyPI artifact URLs only. Future lock regeneration must isolate the private Safety index configured outside the lock.
- The audit found 69 distinct update candidates across runtime, build, development, web, and transitive dependencies. Updates will be applied in controlled slices, excluding major or high-risk pre-1.0 jumps.
- Clawpatch was not allowed to include the dirty tree; its fallback broad review was interrupted and produced no applied changes. Vulture findings remain ignored as false positives.
- Completed the first controlled lock slice in commit `afcc46da32874d93c7a6ecb8f263f35a04c34aae` (`STABILITY_PATCH: update selected dependency lock`, 2026-07-15 12:26:56 -0300). Direct updates cover `idna`, PyQt6, Nuitka, PyInstaller, Black, Filelock, Isort, Mypy, Pytest, Ruff, and Virtualenv.
- Mypy and Virtualenv required the transitive updates `ast-serialize 0.6.0`, `librt 0.13.0`, `pyinstaller-hooks-contrib 2026.6`, and `python-discovery 1.4.4`. Click `8.4.2` and Pillow `12.3.0` are also present from the previous authorized lock update.
- Full validation passed: `2526 passed, 6 skipped, 2 warnings, 11 subtests passed`; all lock, type, lint, package integrity, security, import, PyInstaller, and Nuitka checks passed.
- Remaining major, high-risk pre-1.0, and Streamlit-discrepancy candidates remain deferred.

## [v4.45] - 2026-07-11 - HARDENING PYQT6 (ESTABILIZACAO RECUPERADA)

### Recovery and stabilization - 2026-07-12
- Archived and removed the interrupted, uncommitted Cycle 4 mixin/XLSX patch before applying any forward fix.
- Kept Theme/Event/Display mixin extraction deferred; event, resize, theme and headless behavior remain in the stable implementation.
- Window close now remains refused until every owned or retired worker has actually stopped; native Qt deletion is classified without forced termination.
- PaiApi cancellation is terminal through staging and SQLite import, with ownership retained until native thread completion and no success signal after cancel.
- SQLite progress cancellation is classified with `SQLITE_INTERRUPT=9`; DataLoader distinguishes expected cancellation from callback or startup failures.
- AdvancedOptions rejects stale generations and does not rebuild controls while a user selection is waiting for the apply timer.
- Derivadas completion is exactly once, including timeout followed by a late result.
- XLSX limits are canonical across extractor, staging, PAI, robust importer, Derivadas, CLI and trusted full rescan: 64 external files, 128 MiB per file, 1 GiB per batch and 1 GiB expanded ZIP content per file.
- Details refresh uses a bounded fingerprint sample when a data revision token is available, while preserving the exact full hash path without a token.
- Global filter clear now synchronizes quick status buttons; silent fallback failures in touched runtime paths are logged.
- Dead-code review removed only the obsolete Derivadas lock allocation; Qt callbacks, slots, eventFilter, resize and dynamic theme binding were retained.

### Changed
- Promoted local baseline to `4.45` as start of hardening PyQt6 refactor cycle.
- Synchronized runtime metadata in `VERSION`, `config/version.json`, `pyproject.toml` and `uv.lock`.
- Detailed plan attached at `docs/HARDENING_PYQT6_V4_45_PLAN.md`.

### P0 - Critical races fixed (4 HOTFIX_BLOCKER commits)
- `97c70fee` Explicit shutdown() prevents QThread destroyed warning and PaiApi use-after-free.
- `77da4621` SQLite progress_handler cancellation makes long queries interruptible.
- `33ab54a4` PaiApiRefreshWorker cancel() + cleanup stops ThreadPoolExecutor and subprocesses on close.
- `32688ed4` Advanced filter options computation moved off GUI thread (was blocking event loop).

### P1 - Performance/cancel/dedup (6 STABILITY_PATCH + 1 HOTFIX_BLOCKER)
- `f7be4429` ListExportWorker cancellable on shutdown.
- `1753b897` FilterWorker snapshots df_completo (shallow copy) to prevent pandas data race.
- `161f6355` busy_timeout=5000 on read connections prevents database locked under schema changes.
- `a415a9df` Unified 5 duplicate _quote_identifier copies into shared identifier_utils.quote_identifier.
- `cf6ee9d4` XLSX import limits enforced (64 files, 128 MiB each, 1 GiB batch).
- `28773ef3` Fixed derivadas_sync timeout-vs-delivery race (late results no longer lost).

### P2 - Cleanup (5 commits)
- `5f0f52b6` Removed 10 confirmed dead files (1119 lines deleted).
- `389cb892` Removed dead rescan_button widget.
- `76f4c025` Removed 4 empty debug placeholders from tests/.
- `02d1e22c` Documented retrocompat shims as removal candidates.
- `ae55f60c` Narrowed except Exception to RuntimeError/AttributeError in shutdown paths.
- `33dc6837` Replaced silent except pass in PaiApi cancel with logged RuntimeError (bandit B110).

### P3 - God Class decomposition - DEFERRED
- Extraction of Theme/Event/Display mixins degenerated into local patchwork
  (8+ module-global dependencies per mixin). Deferred by user decision.
- See `docs/HARDENING_PYQT6_V4_45_PLAN.md` Ciclo 4 section for future approaches.

### Deferred items (with technical justification)
- Slice 2.5/2.6 (unify SSA normalization / date parsing): 3 sources have different
  contracts (storage strict vs display compat). Requires product decision.
- Slice 3.3 (consolidate v1/v2 scripts): v1 referenced by test_stream_log_wrapper_guards.
- Slice 3.4 (unify Qt stubs): qt_stubs.py and headless_qt_stubs.py are complementary,
  not duplicates. Broad refactor of 7+ modules.
- Full except Exception triage (770 occurrences): only critical paths narrowed.

### Validation
- `ruff check .`: All checks passed.
- `ty check`: All checks passed (on touched files).
- `semgrep` p/python + p/owasp-top-ten: 0 findings on 15 touched files.
- `bandit`: 0 issues on touched files (1 B110 fixed).
- Focused pytest: 1000+ tests passed across database, GUI, PaiApi, filter, derivadas suites.
- XLSX focused validation: 137 tests passed; trusted preflight scanned 1767 files / 538283881 bytes in 0.378 s with no material RSS increase.
- AdvancedOptions/Derivadas caller validation: 588 tests passed and 1 skipped.
- Real GUI smoke loaded 96028 rows and validated pagination, simple/advanced filters, clear, details, links, Derivadas graph, theme, resize and native close.
- Five-run medians after the GUI performance fix: render 0.278 s, simple filter 0.238 s, advanced filter 0.238 s, details 0.011 s; RSS improved by about 29 MiB.
- `pip-audit`, gitleaks and verified-only trufflehog: no vulnerabilities or verified leaks.
- Preserved `v4.36` as the latest published remote tag.

## [v4.44] - 2026-07-06

### Changed
- Promoted local active baseline to `4.44`.
- Synchronized runtime metadata in `VERSION`, `config/version.json`, `pyproject.toml` and `uv.lock`.
- Fixed local validation gates for the v4.44 baseline:
  - `scripts/run_tests.sh` no longer depends on Bash `mapfile`, preserving macOS system Bash compatibility.
  - `tests/test_gui_stability.py` now accepts official `data_cadastro` header variants.
- Preserved `v4.36` as the latest published remote tag.

### Validation
- `bash -n scripts/run_tests.sh`
- `shellcheck scripts/run_tests.sh`
- `ruff check .`
- `pytest -q tests`: `2455 passed, 6 skipped, 2 warnings, 11 subtests passed`

## [v4.43+ local] - 2026-06-27

### Changed
- Local top on `dev` after baseline `4.43`:
  - Advanced filter option refresh now skips the cache helper entirely on clean cache hits, while dirty refresh still recomputes values.
  - Filter worker cancel/race coverage now includes a real `QThread` cancel while `apply_general_search_terms()` is running.
  - Advanced filter mask failures now keep the displayed dataframe and `filtered_status_label` count in sync instead of showing `0 de 0 SSAs`.
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

### Deferred
- Deep-copy reduction in filter caches remains deferred because current contracts require mutation isolation for cached and returned dataframes.
- Derivadas tree vectorization remains deferred: the tested vectorized attempt was slower than the existing `itertuples()` path on the local 50k-row benchmark.
- `has_post_search_filters` naming/semantics remains deferred because current tests intentionally distinguish terminal-only refresh from general-search sort deferral.

### Validation
- Filtros/cache/GUI validation on the local `v4.43+` cycle:
  - `tests/test_scenario_filter_refresh_mixin_qt.py`: `8 passed`
  - `tests/test_contract_filter_worker_cancel_race.py`: `6 passed`
  - advanced options cache/dirty suite: `41 passed`
  - performance smoke: `4 passed, 1 deselected`
  - combined non-performance slice smoke: `17 passed, 4 deselected`
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
