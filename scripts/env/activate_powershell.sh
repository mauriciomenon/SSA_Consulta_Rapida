#!/usr/bin/env bash
# PowerShell activation script for SSA_Consulta_Rapida (Windows)
# This script automatically detects and activates the correct Python environment

printf '%s\n' '[native-guard] BLOCKED: Bash cannot emulate the Windows environment. Use native PowerShell and direnv_common.ps1.' >&2
return 1 2>/dev/null || exit 1
