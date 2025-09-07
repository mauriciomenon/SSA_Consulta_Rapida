# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

SSA_Consulta_Rapida is a Python 3.13+ application for rapid consultation of SSAs (Support Service Requests) with both CLI and GUI interfaces, featuring Excel import, SQLite database, advanced filtering, and export capabilities.

## Quick Commands

| Task | Command | Notes |
|------|---------|-------|
| **Setup Environment** | `python -m venv .venv && . .venv/Scripts/Activate.ps1` | Windows PowerShell |
| **Setup Environment** | `python -m venv .venv && source .venv/bin/activate` | macOS/Linux |
| **Install Dependencies** | `pip install -r requirements.txt` | Includes PyQt6 for GUI |
| **Run CLI (Default)** | `python main.py` | Standard CLI interface |
| **Run GUI** | `python main.py --gui` | PyQt6 graphical interface |
| **Run Optimized Import** | `python main.py --optimized` | Up to 90% faster for large files |
| **Force Reimport** | `python main.py --force-rescan` | Ignore cache, process all files |
| **Run Tests** | `pytest -q` | Quick test run |
| **Run Specific Tests** | `pytest tests/test_database.py -v` | Run single test file |
| **Check Installation** | `pwsh .\verificar_instalacao.ps1` | Windows verification script |
| **Reset Database** | `python main.py --reset-db` | Destructive: clears all data |

## Architecture Overview

The project follows a modular layered architecture:

**Data Flow**: Excel files → `extracao/` (import) → `armazenamento/` (SQLite) → `core/app_logic.py` (business logic) → `interface/` (CLI/GUI presentation)

**Key Components**:
- **Entry Point**: `main.py` - argument parsing, logging, interface selection
- **Core Logic**: `core/app_logic.py` - import coordination, data validation, error handling  
- **Data Layer**: `armazenamento/database.py` - SQLite operations, schema management
- **Extraction**: `extracao/extractor.py` - Excel parsing with pandas
- **Interfaces**: `interface/cli.py` (terminal) + `gui/gui_ssa.py` (PyQt6)
- **Configuration**: `config/` - JSON files for column mappings, display preferences, settings

The application uses a sophisticated filtering system supporting regex, prefix/suffix matching, negation, and configurable defaults. Both interfaces maintain feature parity for search, filter, sort, and export operations.

## Development Workflows

### Standard Development Cycle
1. **Branch**: Create feature branch from main
2. **Code**: Make changes, test locally with `python main.py`
3. **Test**: Run `pytest -q` for quick validation  
4. **Lint**: Code follows project patterns (no enforced linting currently)
5. **Commit**: Use descriptive messages, reference issues if applicable

### Testing Strategy
- **Unit Tests**: `tests/test_*.py` - individual component testing
- **Integration Tests**: `tests/test_*_verification.py` - cross-component validation
- **Performance Tests**: `tests/performance_tests.py` - benchmark critical operations
- **GUI Tests**: `tests/test_gui_*.py` - interface-specific validation
- **Legacy Tests**: `tests/legacy_tests/` - maintained for compatibility

### Database Development
- **Local DB**: `data/ssas.db` (SQLite, auto-created)
- **Schema**: `config/schema.sql` - current structure  
- **Migrations**: Manual process, backup created automatically
- **Reset**: `python main.py --reset-db` for clean start

### Configuration Management
- **Settings**: `config/settings.json` - user preferences, display options
- **Column Config**: `config/column_priority.json` - display order, labels, widths
- **Mappings**: `config/display_mappings.json` - internal→display name mapping
- **GUI Prefs**: `config/gui_main_preferences.json` - GUI-specific settings

## Important Development Notes

### Environment Requirements
- **Python**: 3.13+ required (3.11 minimum for Windows builds)
- **Platform**: Windows (primary), macOS/Linux supported
- **GUI**: PyQt6 for graphical interface (optional for CLI-only usage)

### Critical Architecture Patterns
- **Smart Upsert**: Database uses intelligent conflict resolution to prevent duplicates
- **Optimized Mode**: `--optimized` flag enables batch operations and performance tuning
- **Filter Modes**: Advanced 5-option filtering (contains, starts, ends, exact, regex) with negation support
- **Configuration Integrity**: Auto-restoration of corrupted config files with backup system
- **Thread Safety**: GUI operations use QThread for non-blocking data loading

### File Import System
- **Auto-Detection**: Scans `docs_entrada/` for Excel files, processes newest by date/mtime
- **Cache Management**: `data/file_cache.json` tracks processed files, skip unchanged
- **Validation**: Pre-import data validation with detailed error reporting
- **Error Recovery**: Automatic database repair and schema recreation capabilities

### Testing Considerations
- **Headless GUI**: Tests use `QT_QPA_PLATFORM=offscreen` for CI compatibility
- **Isolated Tests**: Database tests use temporary files to avoid conflicts
- **Performance Benchmarks**: Critical path operations have timing validations
- **Legacy Compatibility**: Separate test suite maintains backwards compatibility

## Configuration Status

**All Configuration Inconsistencies Resolved** (as of September 6, 2025):

1. **Python Version Consistency**: All environments now use Python 3.13+ consistently
2. **Clean CI/CD Workflows**: Removed inappropriate Node.js/TypeScript workflow checks  
3. **Standardized Dependencies**: PyQt6 centralized in requirements.txt across all environments
4. **Robust Test Discovery**: CI uses pytest markers with intelligent fallback strategy

See `docs/CONFIGURATION_FIXES_2025-09-06.md` for detailed changes.

## Resources

- **Main Documentation**: `README.md` - comprehensive user guide
- **AI Instructions**: `.github/copilot-instructions.md` - development guidelines  
- **Architecture Details**: `docs/ESTRUTURA_PROJETO.md`
- **Implementation Log**: `docs_saida/CHANGELOG_IMPLEMENTACOES.md`
- **Migration Guide**: `docs/GUIA_MIGRACAO_NOVA_INSTALACAO.md`
- **Maintenance Scripts**: `scripts_manutencao/` - database management, diagnostics
