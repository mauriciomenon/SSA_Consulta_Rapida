# Robust Importer: Design and Behavior

Scope covered by tests and implemented in `utils/robust_importer.py`:

- Header synonyms collapse to canonical names: numero_ssa, situacao, data_cadastro.
- Coalescence row-by-row when multiple semantic columns exist.
- Strict numero_ssa normalization via `core.numero_ssa.normalize_strict`.
- Date parsing: ISO, dd/mm/yyyy, and Excel serial to `YYYY-MM-DD` strings.
- Deduplicate by numero_ssa keeping the most recent date row.

API: `import_excel_robust(file_path) -> (DataFrame, stats_dict)`

Stats include:
- duplicate_rows_dropped
- invalid_numero_ssa_rows
- date_parse_failures per column

Notes:
- The implementation is intentionally minimal to satisfy current tests.
- Future: extend header dictionary and add logging/tracing toggles.
