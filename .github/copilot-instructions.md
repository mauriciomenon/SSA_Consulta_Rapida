# AI Coding Agent Instructions - SSA Consulta Rápida

## Project Overview
**SSA Consulta Rápida** is a mature Python-based system for rapid consultation of SSAs (Solicitações de Serviços de Apoio - Support Service Requests). Built with PyQt6 GUI, SQLite database, and comprehensive CLI interface. Current version: v3.0.6, targeting v3.0.7.

## Critical Rules - Read First
- **NEVER** modify `core/`, `armazenamento/`, `extracao/` without backup
- **NEVER** delete `data/ssas.db` (main database)
- **ALWAYS** read `REGRAS_DE_OURO.md` and `ESTRUTURA_PROJETO.md` before making changes
- **TEST** in `scripts_desenvolvimento/` before production changes
- Use `scripts_manutencao/` for maintenance scripts

## Architecture Patterns
- **Entry Point**: `main.py` with comprehensive CLI argument parsing
- **Database**: SQLite via `armazenamento/database.py` with optimized upsert operations
- **GUI Framework**: PyQt6 with width management systems (`gui/simple_width_manager.py`)
- **Data Processing**: Pandas for Excel import/export via `extracao/extractor.py`
- **Configuration**: JSON files in `config/` for mappings and settings

## Development Workflow
1. **Read First**: `TRANSICAO_CONVERSA_v3.0.7.md` for current context
2. **Verify State**: Run `.\verificar_instalacao.ps1` before starting
3. **Test Changes**: Use `scripts_desenvolvimento/` for experimentation
4. **Document**: Update relevant `.md` files with changes
5. **Maintain Compatibility**: Keep CLI/GUI parity and backward compatibility

## Key File Patterns
- **Configuration**: `config/*.json` (critical for column mappings)
- **Core Logic**: `core/app_logic.py` (import/update coordination)
- **Database**: `armazenamento/database.py` (SQLite operations)
- **GUI**: `gui/gui_ssa*.py` (interface implementations)
- **CLI**: `interface/cli_*.py` (command-line interface)

## Code Quality Standards
- **No Debug Messages**: Remove all `DEBUG` prints in production code
- **Robust Error Handling**: Defensive checks for null/undefined values
- **Resource Cleanup**: Proper thread management and cleanup
- **Professional UX**: Clean interfaces, consistent formatting

## Performance Considerations
- **Optimized Mode**: Use `--optimized` flag for large file imports
- **Smart Caching**: Leverage `utils/caching.py` for repeated operations
- **Database Efficiency**: Use batch operations for bulk inserts/updates
- **Memory Management**: Monitor memory usage in large data operations

## Common Tasks
- **Import Issues**: Check `scripts_manutencao/debug_*.py` for diagnostics
- **Database Problems**: Use `scripts_manutencao/verificar_integridade.py`
- **GUI Crashes**: Focus on thread cleanup and QThread management
- **CLI Navigation**: Ensure consistent pagination and table formatting

## Version Management
- **Semantic Versioning**: Follow pattern v3.0.x for patches
- **Changelog**: Update `CHANGELOG_IMPLEMENTACOES.md` for changes
- **Release Notes**: Document in `RELEASE_NOTES_*.md` format
- **Migration**: Create guides in `GUIA_MIGRACAO_*.md` for major changes

## Testing Strategy
- **Quick Tests**: `scripts_desenvolvimento/simple_test.py`
- **Integration**: `tests/` directory with organized test suites
- **Manual Verification**: Use `scripts_manutencao/verificar_*.py`
- **User Scenarios**: Test both CLI and GUI workflows

## Documentation Style
- **Clear Headers**: Use standard Markdown headers with clear hierarchy
- **Step-by-Step**: Provide exact commands and file paths
- **Status Tracking**: Mark completed/pending items clearly
- **Cross-References**: Link related files and documentation

## Environment Requirements
- **Python 3.13+** with virtual environment setup
- **Windows PowerShell** as default shell (provide .ps1 scripts)
- **PyQt6** for GUI components
- **Pandas** for data manipulation
- **SQLite** for database operations

## For New AI Agents
1. Start with `TEMPLATE_NOVA_CONVERSA.md` for onboarding
2. Execute verification scripts to confirm environment
3. Review `CHECKLIST_PENDENCIAS_v3.0.7.md` for current priorities
4. Focus on incremental improvements over major rewrites
