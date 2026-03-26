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

  $existingRaw = & pyenv virtualenvs --bare
  if ($LASTEXITCODE -ne 0) { throw "Falha ao listar virtualenvs do pyenv-win." }
  $existing = $existingRaw -split "`n" | ForEach-Object { $_.Trim() }
  if ($existing -contains $VenvName) {
    Write-Host "[ok] Virtualenv '$VenvName' já existe"
  } else {
    Write-Host "[info] Criando virtualenv '$VenvName'"
    $listRaw = & pyenv install -l
    if ($LASTEXITCODE -ne 0) { throw "Falha ao listar versoes do pyenv-win." }
    $list = $listRaw -split "`n" | ForEach-Object { $_.Trim() }
    $ver = $null
    foreach ($major in @('3.13', '3.12', '3.11', '3.10')) {
      $candidate = $list | Where-Object { $_ -match ("^{0}\.[0-9]+$" -f [regex]::Escape($major)) } | Select-Object -Last 1
      if ($candidate) {
        $ver = $candidate
        break
      }
    }
    if (-not $ver) { throw "Nao foi possivel descobrir versao Python suportada (3.13-3.10) no pyenv-win." }
    pyenv install -s $ver
    if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar Python $ver via pyenv-win." }
    pyenv virtualenv $ver $VenvName
    if ($LASTEXITCODE -ne 0) { throw "Falha ao criar virtualenv $VenvName." }
  }

  # Ativa sem alterar .python-version
  pyenv activate $VenvName
  if ($LASTEXITCODE -ne 0) { throw "Falha ao ativar virtualenv '$VenvName'." }
  python -m pip install -U pip
  if ($LASTEXITCODE -ne 0) { throw "Falha ao atualizar pip no ambiente '$VenvName'." }
  python -m pip install -r requirements.txt
  if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar requirements.txt no ambiente '$VenvName'." }
}

Ensure-PyenvWin
Ensure-VirtualEnv

Write-Host "[ok] Ambiente pronto. Abra um novo terminal para garantir PATH atualizado (se acabou de instalar pyenv-win)."

