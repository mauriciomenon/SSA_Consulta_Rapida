#Requires -Version 7
# Lista "sha256  nome" dos ZIPs do alvo, no formato do shasum (BUILD_WINDOWS_VM_SSH.md, passo 4).
# Uso: pwsh -NoProfile -ExecutionPolicy Bypass -File dev_env\build\vm_zip_sha256.ps1 [-Platform windows_amd64]
param([string] $Platform = "windows_amd64")
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$packages = Join-Path $repoRoot "builds\packages\$Platform"
Get-ChildItem -Path $packages -Filter "*.zip" | Sort-Object Name | ForEach-Object {
    (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLower() + "  " + $_.Name
}
