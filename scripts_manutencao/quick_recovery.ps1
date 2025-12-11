Param(
    [ValidateSet("checkpoint","restore","apply-patch","help")]
    [string]$Action = "checkpoint",
    [string]$Message = "pre-reboot",
    [string]$PatchPath = ""
)

$ErrorActionPreference = 'Stop'

function Write-Header($text) {
    Write-Host "=== $text ===" -ForegroundColor Cyan
}

function Get-Timestamp {
    return (Get-Date -Format 'yyyyMMdd_HHmmss')
}

function New-RecoveryPackage([string]$ts) {
    $dir = Join-Path 'docs_saida' "SESSION_RECOVERY_$ts"
    New-Item -ItemType Directory -Force -Path $dir | Out-Null

    git rev-parse --abbrev-ref HEAD | Set-Content (Join-Path $dir 'branch.txt')
    git rev-parse HEAD | Set-Content (Join-Path $dir 'commit.txt')
    git status --porcelain=v1 | Set-Content (Join-Path $dir 'status.txt')
    git diff --name-only | Set-Content (Join-Path $dir 'changed_files.txt')
    git diff | Set-Content (Join-Path $dir 'uncommitted.patch')

    @(
        "Recovery timestamp: $ts",
        "1) Apos o reboot, no diretorio do repo:",
        "   - Verifique stashes: git stash list",
        "   - Aplique o ultimo checkpoint: git stash pop",
        "   - Alternativa: git apply $(Join-Path 'docs_saida' "SESSION_RECOVERY_$ts" 'uncommitted.patch')",
        "2) Revalidar testes: pytest -q",
        "3) Continuar pelo arquivo/fluxo atual conforme sua sessao"
    ) | Set-Content -Encoding UTF8 (Join-Path $dir 'README_RECOVERY.txt')

    return $dir
}

function Do-Checkpoint([string]$msg) {
    $ts = Get-Timestamp
    Write-Header "Criando pacote de recuperacao ($ts)"
    $dir = New-RecoveryPackage -ts $ts

    Write-Header "Criando stash com untracked"
    $stashMsg = "WIP $msg $ts"
    git stash push -u -m $stashMsg | Out-Null

    Write-Host "- Stash criado: $stashMsg" -ForegroundColor Green
    Write-Host "- Pacote: $dir" -ForegroundColor Green
}

function Do-Restore() {
    Write-Header "Stashes disponiveis"
    git stash list
    Write-Host "\nPara aplicar o mais recente: git stash pop" -ForegroundColor Yellow
}

function Do-ApplyPatch([string]$path) {
    if (-not $path -or -not (Test-Path $path)) {
        $example = Join-Path 'docs_saida' 'SESSION_RECOVERY_YYYYMMDD_HHMMSS' 'uncommitted.patch'
        throw "Informe um PatchPath valido (ex.: $example)"
    }
    Write-Header "Aplicando patch: $path"
    git apply --reject --whitespace=fix $path
    Write-Host "Patch aplicado (verifique conflitos .rej, se houver)." -ForegroundColor Green
}

function Show-Help() {
    @"
Uso:
  pwsh -File scripts_manutencao/quick_recovery.ps1 -Action checkpoint [-Message "rotulo"]
  pwsh -File scripts_manutencao/quick_recovery.ps1 -Action restore
  pwsh -File scripts_manutencao/quick_recovery.ps1 -Action apply-patch -PatchPath <caminho>

Acoes:
  checkpoint  Cria stash (-u) e pacote docs_saida/SESSION_RECOVERY_<ts> com diff/instrucoes.
  restore     Lista stashes para voce aplicar (git stash pop). Nao aplica automaticamente.
  apply-patch Aplica um patch salvo (ex.: uncommitted.patch) com git apply.

Exemplos:
  # Checkpoint rapido com rotulo
  pwsh -File scripts_manutencao/quick_recovery.ps1 -Action checkpoint -Message "pre-reboot"

  # Apos reiniciar: ver e aplicar
  pwsh -File scripts_manutencao/quick_recovery.ps1 -Action restore
  git stash pop

  # Alternativa com patch salvo
  pwsh -File scripts_manutencao/quick_recovery.ps1 -Action apply-patch -PatchPath $(Join-Path 'docs_saida' 'SESSION_RECOVERY_20250101_120000' 'uncommitted.patch')
"@
}

try {
    switch ($Action) {
        'checkpoint'   { Do-Checkpoint -msg $Message }
        'restore'      { Do-Restore }
        'apply-patch'  { Do-ApplyPatch -path $PatchPath }
        Default        { Show-Help }
    }
}
catch {
    Write-Error $_
    exit 1
}

