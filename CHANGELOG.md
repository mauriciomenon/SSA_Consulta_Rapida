# Changelog

All notable changes to this project are documented in this file.

## [Unreleased] - 2025-11-10

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
