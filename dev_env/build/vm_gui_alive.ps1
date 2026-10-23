#Requires -Version 7
# Confere se a GUI empacotada abre e fica viva (BUILD_WINDOWS_VM_SSH.md, passo 4).
# Uso: pwsh -NoProfile -ExecutionPolicy Bypass -File dev_env\build\vm_gui_alive.ps1 [-Platform windows_amd64]
param([string] $Platform = "windows_amd64", [int] $Seconds = 25)
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$exe = Get-ChildItem -Path (Join-Path $repoRoot "launchers\dist\$Platform") -Recurse -Filter "SSA_GUI_*.exe" |
    Select-Object -First 1
if ($null -eq $exe) {
    throw "GUI empacotada nao encontrada em launchers\dist\$Platform"
}
$bytes = [IO.File]::ReadAllBytes($exe.FullName)
$peOffset = [BitConverter]::ToInt32($bytes, 0x3C)
"PE machine: 0x{0:X4} ({1})" -f [BitConverter]::ToUInt16($bytes, $peOffset + 4), $exe.Name

$env:QT_QPA_PLATFORM = "offscreen"
$process = Start-Process -FilePath $exe.FullName -PassThru
Start-Sleep -Seconds $Seconds
$process.Refresh()
if ($process.HasExited) {
    "GUI_SAIU exit=$($process.ExitCode)"
    exit 1
}
"GUI_VIVA apos $Seconds s"
Stop-Process -Id $process.Id -Force
