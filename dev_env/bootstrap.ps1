# Requires: PowerShell 5+ (Windows 10/11)
param(
  [string]$VenvName,
  [switch]$AllowRemotePyenvInstall,
  [string]$PyenvInstallerSha256
)

$ErrorActionPreference = 'Stop'

function Test-CommandAvailable($Name) {
  try { Get-Command $Name -ErrorAction Stop | Out-Null; return $true } catch { return $false }
}

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $ProjectRoot

if (-not $VenvName) {
  if (Test-Path .\.python-version) {
    $VenvName = Get-Content .\.python-version | Select-Object -First 1
  }
}
if (-not $VenvName) { $VenvName = 'ssa_consulta_rapida_py313' }

Write-Output "[info] Virtualenv alvo: $VenvName"

function Install-PyenvWin([switch]$AllowRemoteInstall, [string]$InstallerSha256) {
  if (Test-CommandAvailable pyenv) { Write-Output "[ok] pyenv-win encontrado"; return }
  if (-not $AllowRemoteInstall) {
    Write-Warning "pyenv-win nao encontrado. Instalacao remota desabilitada; usando fallback com Python do sistema. Use -AllowRemotePyenvInstall para aceitar o instalador remoto oficial."
    return
  }
  if ([string]::IsNullOrWhiteSpace($InstallerSha256)) {
    Write-Warning "Instalacao remota do pyenv-win exige -PyenvInstallerSha256. Usando fallback com Python do sistema."
    return
  }
  Write-Output "[info] Instalando pyenv-win (pode solicitar permissoes)"
  try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
  } catch {
    Write-Warning "Nao foi possivel forcar TLS 1.2 antes do download do pyenv-win."
  }
  $installerPath = Join-Path ([System.IO.Path]::GetTempPath()) 'pyenv-win-install.ps1'
  try {
    Write-Output "[info] Baixando instalador pyenv-win: https://pyenv.win/install.ps1"
    Invoke-WebRequest -UseBasicParsing -Uri 'https://pyenv.win/install.ps1' -OutFile $installerPath
    $actualHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $installerPath).Hash.ToLowerInvariant()
    $expectedHash = $InstallerSha256.Trim().ToLowerInvariant()
    if ($actualHash -ne $expectedHash) {
      throw "Hash SHA256 do instalador pyenv-win nao confere. Esperado=$expectedHash Obtido=$actualHash"
    }
    if (Get-Command -Name Unblock-File -ErrorAction SilentlyContinue) {
      try {
        Unblock-File -LiteralPath $installerPath -ErrorAction Stop
      } catch {
        Write-Warning "Nao foi possivel remover Mark-of-the-Web do instalador pyenv-win."
      }
    }
    $powershellExe = (Get-Command -Name powershell.exe -ErrorAction Stop).Source
    & $powershellExe -NoProfile -ExecutionPolicy Bypass -File $installerPath
    if ($LASTEXITCODE -ne 0) {
      throw "Instalador pyenv-win terminou com codigo $LASTEXITCODE."
    }
  } finally {
    Remove-Item -LiteralPath $installerPath -Force -ErrorAction SilentlyContinue
  }
  $env:Path = "$env:USERPROFILE\.pyenv\pyenv-win\bin;$env:USERPROFILE\.pyenv\pyenv-win\shims;" + $env:Path
}

function Initialize-VirtualEnv() {
  if (-not (Test-CommandAvailable pyenv)) {
    Write-Warning "pyenv-win nao disponivel; criando fallback .venv com python do sistema"
    if (-not (Test-CommandAvailable python)) { throw "Python nao encontrado no PATH." }
    python -m venv .venv
    . .\.venv\Scripts\Activate.ps1
    python -m pip install -U pip
    python -m pip install -r requirements.txt
    Write-Output "[ok] Ambiente .venv criado (fallback)."
    return
  }

  $existingRaw = & pyenv virtualenvs --bare
  if ($LASTEXITCODE -ne 0) { throw "Falha ao listar virtualenvs do pyenv-win." }
  $existing = $existingRaw -split "`n" | ForEach-Object { $_.Trim() }
  if ($existing -contains $VenvName) {
    Write-Output "[ok] Virtualenv '$VenvName' ja existe"
  } else {
    Write-Output "[info] Criando virtualenv '$VenvName'"
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

Install-PyenvWin -AllowRemoteInstall:$AllowRemotePyenvInstall -InstallerSha256 $PyenvInstallerSha256
Initialize-VirtualEnv

Write-Output "[ok] Ambiente pronto. Abra um novo terminal para garantir PATH atualizado (se acabou de instalar pyenv-win)."

