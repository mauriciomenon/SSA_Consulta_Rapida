param(
  [string]$Python = "python",
  [switch]$Upload,
  [switch]$OneFile = $true
)

$ErrorActionPreference = 'Stop'
$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent
Set-Location $ROOT

# 1) Lê versão
$versionJson = Get-Content (Join-Path $ROOT 'config/version.json') -Raw | ConvertFrom-Json
$VER = $versionJson.version_short
if (-not $VER) { $VER = '0.0.0' }
$TAG = "v$VER"

# 2) Cria venv local
$venv = Join-Path $ROOT '.venv_build'
if (-not (Test-Path $venv)) { & $Python -m venv $venv }
$pip = Join-Path $venv 'Scripts/pip.exe'
$py = Join-Path $venv 'Scripts/python.exe'

# 3) Instala dependências (inclui PyQt6 e PyInstaller para Windows)
& $pip install --upgrade pip > $null
& $pip install -r (Join-Path $ROOT 'requirements.txt') > $null
& $pip install PyQt6 pyinstaller > $null

# 4) Limpa dist/build
Remove-Item -Recurse -Force (Join-Path $ROOT 'build') -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force (Join-Path $ROOT 'dist') -ErrorAction SilentlyContinue

# 5) PyInstaller – CLI e GUI
$common = @('--clean','--noconfirm')
if ($OneFile) { $common += '--onefile' }

# CLI (console)
& $py -m PyInstaller @common --name 'ssa_cli' (Join-Path $ROOT 'main.py')

# GUI (janela, sem console)
& $py -m PyInstaller @common --windowed --name 'ssa_gui' (Join-Path $ROOT 'launchers/gui_launcher.pyw')

# 6) Empacota ZIP
$zipName = "SSA_Consulta_Rapida_${VER}_windows.zip"
$zipPath = Join-Path (Join-Path $ROOT 'dist') $zipName
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }

$files = @()
$cli = Join-Path (Join-Path $ROOT 'dist') 'ssa_cli.exe'
$gui = Join-Path (Join-Path $ROOT 'dist') 'ssa_gui.exe'
if (Test-Path (Join-Path $ROOT 'dist/ssa_cli')) { $cli = Join-Path (Join-Path $ROOT 'dist/ssa_cli') 'ssa_cli.exe' }
if (Test-Path (Join-Path $ROOT 'dist/ssa_gui')) { $gui = Join-Path (Join-Path $ROOT 'dist/ssa_gui') 'ssa_gui.exe' }
$files += $cli
$files += $gui

Compress-Archive -Path $files -DestinationPath $zipPath
Write-Host "Artefato gerado:" $zipPath -ForegroundColor Green

# 7) Upload opcional para Release do GitHub
if ($Upload) {
  if ((Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "Enviando asset para release $TAG..." -ForegroundColor Cyan
    gh release upload $TAG $zipPath --clobber
  } else {
    Write-Warning "gh CLI não encontrado. Faça upload manual do arquivo: $zipPath"
  }
}

Write-Host "Concluído." -ForegroundColor Green
