# SSA Consulta Rápida - AI Coding Agent Instructions

## Project Overview
This is a Python application for querying SSA (Solicitação de Serviço de Automação) data with CLI, GUI (PyQt6), and Streamlit web interfaces. The system imports Excel files into SQLite and provides advanced filtering and export capabilities.

## Architecture Patterns

### Entry Points
- `main.py` - Primary entry point supporting `--gui`, `--streamlit`, `--optimized` modes
- `streamlit_app.py` - Web dashboard launched via `python main.py --streamlit`
- `launchers/` - Cross-platform executables (CLI/GUI) with build system

### Core Modules
- `core/app_logic.py` - Import orchestration and cache management
- `core/numero_ssa.py` - **Critical**: Strict 9-digit normalization (YYYY+5 digits, 1980-2050 range)
- `armazenamento/database.py` - SQLite operations with modular sub-components:
  - `database_upsert_logic.py` - Smart merge operations
  - `database_integrity.py` - Verification and repair
  - `numero_ssa_utils.py` - Centralized normalization functions

### Interface Layers
- `interface/cli.py` - Interactive CLI with pagination (`m`/`mais` commands)
- `gui/gui_ssa.py` - Main GUI (2232 lines, not `gui_ssa_poc.py`)
- Three parallel interfaces maintained for feature parity

## Configuration System

### JSON Configuration Files (in `config/`)
- `column_mappings.json` - Excel column → internal field mapping
- `display_mappings.json` - Internal field → display label mapping  
- `column_priority.json` - Column visibility, order, and fixed widths
- `settings.json` - Runtime preferences including `display_settings`
- Auto-restoration via "integrity" functions in `core/config_manager.py`

### Environment Overrides
- `SSA_CONFIG_DIR` - Alternative config directory for testing
- `SSA_EXTRA_DIRS` - Additional directories for `setup_dirs()`

## Development Workflows

### Environment Setup
```powershell
# Windows (recommended)
python -m venv .venv
. .\activate_repo.ps1

# macOS/Linux
source ./activate_repo.sh
```

### Testing
```bash
# Run core tests (67 tests passing)
python -m pytest tests/ -v

# Performance/integration tests
python -m pytest tests/test_performance_import.py -m performance

# Build validation
python launchers/test_complete.py
```

### Build System
- `launchers/build_simple.py` - Development builds (30s)
- `launchers/build_complete.py` - Production builds with UPX compression
- Cross-platform support (Windows, macOS ARM64)

## Key Conventions

### Numero SSA Validation
```python
# Use core.numero_ssa.normalize_strict() - strict 9-digit validation
# Rejects: letters, >9 digits, years outside 1980-2050
# Special case: "YYYY-XXXXX" allowed if last 5 digits not identical
from core.numero_ssa import normalize_strict
canonical = normalize_strict("2025-12345")  # → "202512345" 
invalid = normalize_strict("2025-22222")    # → None (rejected)
```

### Configuration Management
```python
# Always use integrity functions for auto-restoration
from core.config_manager import load_display_mappings_integrity
mappings = load_display_mappings_integrity()  # Creates defaults if missing
```

### Database Operations
```python
# Use context managers for connections
from armazenamento.database import get_db_connection
with get_db_connection(db_path) as conn:
    # Database operations
```

### Logging
- Package logger: `logging.getLogger(__name__)` in modules
- File logs: `logs/ssa.log` (1MB rotation)
- Console: WARNING+ only to keep CLI clean

## Project Structure Patterns

### Module Organization
- `core/` - Business logic, configuration, data processing
- `armazenamento/` - Database layer (split into specialized modules)  
- `interface/` - CLI components and table printing
- `gui/` - PyQt6 interface (main file is `gui_ssa.py`)
- `utils/` - Cross-cutting utilities, setup, caching
- `tests/` - Comprehensive test suite with performance markers

### Directory Auto-Creation
- `utils.setup_project_structure.setup_dirs()` called early in `main.py`
- Creates: `data/`, `logs/`, `reports/`, `exportacao/`, etc.

## Important Notes

### File Processing Priority
When multiple Excel files exist, selection by:
1. Date in filename (YYYYMMDD pattern)
2. File modification time  
3. Situação evolution: ASE → ADI → APL → APG → SPG → SEE → SAD → STE

### Filter Syntax (CLI/GUI parity)
- `OU`/`OR` for alternatives: `ASE OU ADI`
- `!` for negation: `!ASE`
- `^` prefix, `$` suffix, `~` contains matching
- Regex fallback for complex patterns

### Build Artifacts
- Never commit `launchers/dist/` or `launchers/dist_simple/`
- Use `.gitignore` patterns to exclude build outputs
- Test executables with `launchers/test_executables.py`

## Common Tasks

### Adding New Columns
1. Update `config/column_mappings.json` for Excel mapping
2. Add to `config/display_mappings.json` for user-friendly labels
3. Update `config/column_priority.json` for visibility/ordering
4. Test with `python -m pytest tests/test_column_mappings_integrity.py`

### Database Schema Changes  
1. Modify `config/schema.sql` 
2. Use `--reset-db` flag for clean recreation
3. Verify with integrity checks in `armazenamento/database_integrity.py`

### Performance Optimization
- Use `--optimized` mode for large imports (80-90% faster)
- Monitor with `tests/performance_tests.py`
- SQLite optimizations in `database_optimized.py`

## Error Handling Patterns

### Custom Exception Hierarchy
```python
# Use structured exception hierarchy in core/app_logic.py
from core.app_logic import (
    ImporterError,           # Base exception
    DatabaseError,           # Database operations
    DatabaseConnectionError, # Connection issues
    DatabaseCorruptionError, # Data corruption
    DatabaseSchemaError,     # Schema problems
    DatabaseSpaceError,      # Disk space issues
    ExtractionError,         # File extraction
    DataValidationError,     # Data validation
    CacheError              # Cache operations
)
```

### Recovery Strategies
- **Database corruption**: Auto-repair with `database.repair_database_if_needed()`
- **Schema errors**: Auto-recreation with `database.initialize_database()`
- **Connection failures**: Stop processing, log error
- **Extraction errors**: Continue with next file, log warning
- **Validation errors**: Skip invalid data, continue processing

### Optimized Mode Activation
```python
# Enable performance optimizations
from armazenamento.database_optimized import enable_optimized_import
enable_optimized_import()  # Monkey-patches database functions

# Key optimizations: WAL mode, batch operations, temp indexes
# 80-90% faster for large datasets (>5MB Excel files)
```

## Testing Patterns

### Test Organization
```python
# Use pytest markers for test categorization
@pytest.mark.performance      # Performance/load tests
@pytest.mark.integration      # Integration tests  
@pytest.mark.unit            # Unit tests (planned)
@pytest.mark.slow            # Long-running tests
@pytest.mark.legacy          # Legacy compatibility tests
```

### Test Structure
- `tests/conftest.py` - Global fixtures and Qt offscreen setup
- `tests/_helpers/` - Shared test utilities and database helpers
- `tests/performance_tests.py` - Dedicated performance testing suite
- `tests/test_*_integrity.py` - Configuration integrity validation

### Running Tests
```bash
# Core test suite (67 tests passing)
pytest -m "integration and not slow and not legacy" -q

# Performance tests with environment controls
SSA_PERF_ROWS=5000 SSA_PERF_FAST=1 pytest -m performance

# Coverage for main modules
pytest --cov=armazenamento --cov=core --cov-report=term-missing -q
```

## UI/Display Management

### Column Width System
- **CLI**: `interface/cli_width_manager.py` - Terminal-optimized width calculation
- **GUI**: `gui/simple_width_manager.py` - Fixed deterministic widths with proportional growth
- **Configuration**: `column_priority.json` controls visibility, order, fixed_widths
- **Runtime**: User resizing saved in GUI preferences, overrides calculated widths

### Theme Support
```python
# GUI supports multiple themes with persistence
themes = ["Padrão", "Escala de cinza", "Windows 7", "KDE Plasma", "GNOME"]
# Applied via apply_theme() with automatic contrast adjustments
```

### Display Mapping Pipeline
1. **Excel columns** → `column_mappings.json` → **internal fields**
2. **Internal fields** → `display_mappings.json` → **user labels** 
3. **User labels** + `column_priority.json` → **final display**

## Build and Deployment System

### Multi-Platform Build
```bash
# Development builds (30 seconds)
python launchers/build_simple.py gui

# Production builds with optimization
python launchers/build_complete.py --platform windows_amd64 --optimize

# Multi-platform build (current platform only)
python launchers/build_multiplatform.py --all --auto-cleanup
```

### Build Artifacts Management
- **Never commit**: `launchers/dist/`, `launchers/dist_simple/`, `*.log` files
- **Platform structure**: `dist/{platform}/{app}_v{version}_{platform}.{ext}`
- **Auto-cleanup**: `cleanup_build_artifacts()` removes temp files post-build
- **Cross-platform**: Windows (UPX compression), macOS (.app bundles), Linux (standalone)

### Environment Isolation
```python
# Each platform uses isolated virtual environments
platforms/
├── windows_amd64/venv/    # Windows dependencies
├── macos_arm64/venv/      # macOS dependencies  
└── debian_amd64/venv/     # Linux dependencies
```

## Cache and Performance Patterns

### Import Caching
- **File tracking**: `data/file_cache.json` prevents re-importing unchanged files
- **Force override**: `--force-rescan` ignores cache, processes all files
- **Cache invalidation**: Based on file modification time and size

### Memory Management  
```python
# Large dataset handling with chunking
for chunk in pd.read_excel(filepath, chunksize=10000):
    processed_chunk = process_chunk(chunk)
    save_chunk_to_db(processed_chunk)
```

### Database Performance Optimizations
```sql
-- Optimized SQLite settings for large imports
PRAGMA journal_mode=WAL;        -- Concurrent read/write
PRAGMA synchronous=NORMAL;      -- Balance safety/speed  
PRAGMA cache_size=10000;        -- 10MB cache
PRAGMA mmap_size=268435456;     -- 256MB memory-mapped I/O
```
