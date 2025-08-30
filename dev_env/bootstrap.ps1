# Requires: PowerShell 5+ (Windows 10/11)
param(
  [string]$VenvName
)

$ErrorActionPreference = 'Stop'

function Have-Cmd($name) {
  try { Get-Command $name -ErrorAction Stop | Out-Null; return $true } catch { return $false }
}

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $ProjectRoot

if (-not $VenvName) {
  if (Test-Path .\.python-version) {
    $VenvName = Get-Content .\.python-version | Select-Object -First 1
  }
}
if (-not $VenvName) { $VenvName = 'ssa_consulta_rapida_py313' }

Write-Host "[info] Virtualenv alvo: $VenvName"

function Ensure-PyenvWin() {
  if (Have-Cmd pyenv) { Write-Host "[ok] pyenv-win encontrado"; return }
  Write-Host "[info] Instalando pyenv-win (pode solicitar permissões)"
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
  Invoke-Expression ((Invoke-WebRequest -UseBasicParsing -Uri 'https://pyenv.win/install.ps1').Content)
  $env:Path = "$env:USERPROFILE\.pyenv\pyenv-win\bin;$env:USERPROFILE\.pyenv\pyenv-win\shims;" + $env:Path
}

function Ensure-VirtualEnv() {
  if (-not (Have-Cmd pyenv)) {
    Write-Warning "pyenv-win não disponível; criando fallback .venv com python do sistema"
    if (-not (Have-Cmd python)) { throw "Python não encontrado no PATH." }
    python -m venv .venv
    . .\.venv\Scripts\Activate.ps1
    python -m pip install -U pip
    python -m pip install -r requirements.txt
    Write-Host "[ok] Ambiente .venv criado (fallback)."
    return
  }

  $existing = (& pyenv virtualenvs --bare) -split "`n" | ForEach-Object { $_.Trim() }
  if ($existing -contains $VenvName) {
    Write-Host "[ok] Virtualenv '$VenvName' já existe"
  } else {
    Write-Host "[info] Criando virtualenv '$VenvName'"
    $list = (& pyenv install -l) -split "`n" | ForEach-Object { $_.Trim() }
    $ver = $list | Where-Object { $_ -match '^3\.13\.[0-9]+$' } | Select-Object -Last 1
    if (-not $ver) { throw "Não foi possível descobrir versão 3.13.x no pyenv-win." }
    pyenv install -s $ver
    pyenv virtualenv $ver $VenvName
  }

  # Ativa sem alterar .python-version
  pyenv activate $VenvName
  python -m pip install -U pip
  python -m pip install -r requirements.txt
}

Ensure-PyenvWin
Ensure-VirtualEnv

Write-Host "[ok] Ambiente pronto. Abra um novo terminal para garantir PATH atualizado (se acabou de instalar pyenv-win)."

