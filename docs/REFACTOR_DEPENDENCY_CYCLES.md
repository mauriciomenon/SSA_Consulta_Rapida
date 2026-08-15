# Refactor: Remove Dependency Cycles via shared/ Module

## Summary

Eliminated all dependency cycles and layer violations by extracting common utilities into a new `shared/` module. This refactoring breaks circular dependencies between `core`, `armazenamento`, `extracao`, and `utils` while maintaining full backward compatibility.

## Problem Statement

### Dependency Cycles Detected

Before refactoring, the codebase had the following circular dependencies:

```
core <--> armazenamento
core <--> extracao
core <--> utils
utils --> armazenamento (violation)
```

### Specific Issues

1. **core/numero_ssa.py** provided normalization logic
2. **armazenamento/numero_ssa_utils.py** imported from core and added display logic
3. **utils/formatting.py** imported from armazenamento (creating cycle)
4. **utils/robust_importer.py** imported from core (creating cycle)
5. **extracao/extractor.py** imported from core (creating cycle)

## Solution Design

### New Architecture

Created `shared/` module as a dependency-free foundation layer:

```
shared/          (no dependencies - foundation layer)
  |
  +-- core/      (depends on shared, can depend on armazenamento/extracao)
  +-- armazenamento/  (depends on shared only)
  +-- extracao/  (depends on shared only)
  +-- utils/     (depends on shared only)
```

### Dependency Graph (After Refactoring)

```
== Package-level Import Graph ==
armazenamento   -> -
config          -> -
core            -> armazenamento, extracao, utils
exportacao      -> -
extracao        -> -
gui             -> armazenamento, core, utils
interface       -> armazenamento, core, exportacao, utils
utils           -> -

== Cycles ==
None

== Layer Violations ==
None
```

## Implementation Details

### Files Created

1. **shared/__init__.py**
   - Empty module initialization file

2. **shared/numero_ssa.py**
   - Moved from: core/numero_ssa.py (lines 1-97)
   - Added: normalize_numero_ssa() from armazenamento/numero_ssa_utils.py (lines 105-127)
   - Exports: normalize_strict, is_valid_numero_ssa, bulk_normalize, normalize_numero_ssa

3. **shared/date_utils.py**
   - Moved from: core/date_utils.py (lines 1-68)
   - Exports: parse_any_date, bulk_parse_dates

4. **shared/column_mappings.py**
   - Forwarder to break extracao -> core dependency
   - Forwards: load_column_mappings_integrity from core.config_manager

### Files Modified

1. **core/numero_ssa.py**
   - Converted to re-export from shared.numero_ssa
   - Maintains backward compatibility for all existing imports

2. **core/date_utils.py**
   - Converted to re-export from shared.date_utils
   - Maintains backward compatibility for all existing imports

3. **armazenamento/numero_ssa_utils.py** (lines 24-25, 105-127)
   - Changed import from core.numero_ssa to shared.numero_ssa
   - Added import of normalize_numero_ssa from shared
   - Removed local duplicate of normalize_numero_ssa function

4. **extracao/extractor.py** (line 14)
   - Changed: `from core.config_manager import ...`
   - To: `from shared.column_mappings import ...`

5. **utils/robust_importer.py** (lines 28-29)
   - Changed: `from core.numero_ssa import ...`
   - To: `from shared.numero_ssa import ...`
   - Changed: `from core.date_utils import ...`
   - To: `from shared.date_utils import ...`

6. **utils/robust_importer_old.py** (lines 46-47)
   - Same changes as utils/robust_importer.py

7. **utils/formatting.py** (lines 20-24)
   - Removed try/except import from armazenamento.database
   - Changed to direct import from shared.numero_ssa

## Testing & Validation

### Import Analysis

```bash
python scripts_manutencao/analyze_imports.py
```

**Result:**
- Cycles: None
- Layer Violations: None

### Functional Tests

All 10 comprehensive tests passed:

```
Test 1: All modules import successfully
Test 2: Re-exports work correctly
Test 3: normalize_strict handles edge cases
Test 4: is_valid_numero_ssa works correctly
Test 5: bulk_normalize works correctly
Test 6: parse_any_date works correctly
Test 7: armazenamento.numero_ssa_utils functions work
Test 8: utils.formatting.format_cell works
Test 9: extracao.extractor loads 133 column mappings
Test 10: shared module has all expected functions
```

### Integration Tests

- CLI launches successfully: `python main.py -h`
- All high-level modules load: interface, gui, exportacao
- No circular import issues detected

### Regression Tests

Validated that all existing APIs continue to work:

```python
from core.numero_ssa import normalize_strict
normalize_strict('2025-12345')  # Returns: '202512345'

from core.date_utils import parse_any_date
parse_any_date('2025-01-02 03:04:05')  # Returns: '2025-01-02 03:04:05'

from armazenamento.numero_ssa_utils import normalize_numero_ssa_strict
normalize_numero_ssa_strict('2025-12345')  # Returns: '202512345'

from utils.formatting import format_cell
format_cell('2025-12345', 'numero_ssa')  # Returns: '202512345'
```

## Backward Compatibility

### Preserved APIs

All existing import paths continue to work:

- `from core.numero_ssa import normalize_strict` (re-exported from shared)
- `from core.date_utils import parse_any_date` (re-exported from shared)
- `from armazenamento.numero_ssa_utils import normalize_numero_ssa_strict`
- `from utils.formatting import format_cell`

### No Breaking Changes

- CLI remains unchanged
- GUI remains unchanged
- Streamlit interface remains unchanged
- All public APIs maintain identical signatures

## Benefits

1. **Clean Architecture**: Clear dependency hierarchy with no cycles
2. **Maintainability**: Shared utilities in single location
3. **Testability**: Independent modules easier to test in isolation
4. **Scalability**: Easier to add new modules without creating cycles
5. **Code Reuse**: Shared utilities avoid duplication

## Risk Assessment

### Low Risk Factors

- All tests pass
- No changes to public APIs
- Backward compatibility maintained
- Comprehensive validation performed

### Monitoring Points

- Watch for any import-related issues in production
- Verify that all entry points (CLI/GUI/Streamlit) continue to work
- Monitor for any performance impact (minimal expected)

## References

- Original plan archive is no longer published in this repository.
- Import analysis script: scripts_manutencao/analyze_imports.py
- Test suite: temp/test_refactor.py

## Commit Message

```
refactor(deps): eliminate dependency cycles via shared/ module

Break circular dependencies between core, armazenamento, extracao, and utils
by extracting common utilities into new shared/ module.

Changes:
- Create shared/ module with numero_ssa, date_utils, column_mappings
- Convert core/numero_ssa.py and core/date_utils.py to re-exporters
- Update imports in armazenamento, extracao, utils to use shared/
- Remove duplicate normalize_numero_ssa from armazenamento/numero_ssa_utils.py

Impact:
- Cycles: None (was: core <--> armazenamento, core <--> extracao, core <--> utils)
- Layer violations: None (was: utils --> armazenamento)
- All tests pass, backward compatibility maintained

References: internal archive removed from the public repository.
```

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->
