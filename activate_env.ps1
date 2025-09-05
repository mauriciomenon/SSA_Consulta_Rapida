<#
  activate_env.ps1
  - Ativa venv preferindo '.venv_build' > '.venv'
  - Respeita pyenv (.python-version) e direnv (.envrc) quando presentes
  - Forca UTF-8 para evitar UnicodeEncodeError no Windows
#>

# UTF-8 para console e Python
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::InputEncoding  = [System.Text.UTF8Encoding]::new()
$env:PYTHONUTF8$env:PYTHONIOENCODING
# Respeitar direnv, se configurado
if (Get-Command direnv -ErrorAction SilentlyContinue) {
  if (Test-Path '.envrc') {
    try { direnv export powershell | Invoke-Expression } catch {}
  }
}

# Selecionar python via pyenv, se disponivel
$pythonCmd = $null
if ((Test-Path '.python-version') -and (Get-Command pyenv -ErrorAction SilentlyContinue)) {
  $pythonCmd = { pyenv exec python }
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
  $pythonCmd = { python }
} else {
  $pythonCmd = { py }
}

# Escolher venv existente: .venv_build > .venv
$venvDir = if (Test-Path '.venv_build') { '.venv_build' } elseif (Test-Path '.venv') { '.venv' } else { '.venv' }
$venvCreated = $false

if (-not (Test-Path $venvDir)) {
  Write-Host "Criando ambiente virtual em '$venvDir'..."
  & $pythonCmd -m venv $venvDir
  if ($LASTEXITCODE -ne 0) { throw "Falha ao criar venv em $venvDir" }
  $venvCreated = $true
}

Write-Host "Ativando ambiente virtual '$venvDir'..."
. "$venvDir\Scripts\Activate.ps1"

# Garantir pip funcional
if (-not (Get-Command pip -ErrorAction SilentlyContinue)) {
  & $pythonCmd -m ensurepip -U | Out-Null
  & $pythonCmd -m pip install -U pip | Out-Null
}

# Instalar requisitos apenas quando a venv foi criada agora ou quando explicitamente solicitado
if (Test-Path 'requirements.txt') {
  if ($venvCreated -or $env:SSA_AUTO_INSTALL_REQ -eq '1') {
    Write-Host 'Instalando dependencias (requirements.txt)...'
    pip install -r requirements.txt
  }
}

Write-Host 'Ambiente Python configurado (UTF-8 ativo).'
Write-Host 'Para desativar: deactivate'

