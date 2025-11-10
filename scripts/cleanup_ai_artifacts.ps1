<#
Purpose: Move AI-related instructions/evaluations and TODO/checklist docs out of the repo into a local, gitignored folder.
This script copies each item to local_ai_private/ then removes it from the working tree and (optionally) stages deletion via git.

Usage (PowerShell):
  pwsh -File scripts/cleanup_ai_artifacts.ps1

Flags:
  -NoGit     Skip running git commands; only copy and remove files locally.

Notes:
- Destination folder local_ai_private/ is gitignored.
- A migration log will be written to local_ai_private/MIGRATION_LOG.txt
#>
param(
  [switch]$NoGit
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Ensure-Dir($path) {
  if (-not (Test-Path $path)) {
    New-Item -ItemType Directory -Path $path -Force | Out-Null
  }
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Resolve-Path (Join-Path $scriptDir '..')
$destRoot = Join-Path $root 'local_ai_private'
Ensure-Dir $destRoot

$items = @(
  '.github/copilot-instructions.md',
  'gemini.md',
  'temp_claude.txt',
  'docs/ANALISE_PERFORMANCE_QWEN3CLI.md',
  'docs/avaliacao_codigo_gemini.md',
  'docs/avaliacao_codigo_gemini.html',
  'docs/LOG_CONFIGURACAO_COPILOT_COMPLETA_20250907.md',
  'docs/SESSION_CONTEXT_SNAPSHOT_20250915.md',
  'docs/SESSION_SECURITY_OPERATIONS_20250915.md',
  'docs/LICOES_APRENDIDAS.md',
  'docs/CHECKLIST_ACOES_IMEDIATAS.md',
  'docs/CHECKLIST_MASTER.md',
  'docs/CHECKLIST_PENDENCIAS_FUTURAS.md',
  'docs/CHECKLIST_PENDENCIAS_v3.10.md',
  'docs/NEXT_STEPS_AFTER_CONFIG_FIXES.md',
  'docs/PLANOS_MELHORIAS.md',
  'docs/PLANEJAMENTO_ROADMAP.md',
  'docs/PROXIMOS_PASSOS_POS_CONSOLIDACAO.md',
  'docs/ORDENS_E_PLANO_DE_ACAO.md',
  'docs/SECRET_HISTORY_REPORT.md',
  'docs/RELATORIO_CONSOLIDACAO_FINAL.md',
  'docs/RELATORIOS_DESENVOLVIMENTO.md',
  'docs/RELATORIOS_TECNICOS.md',
  'docs/RESUMO_ORGANIZACAO_FINAL.md'
)

$dirs = @(
  '.claude'
)

$logPath = Join-Path $destRoot 'MIGRATION_LOG.txt'
$timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
"[$timestamp] Starting AI/TODO artifacts migration" | Out-File -FilePath $logPath -Encoding utf8 -Append

# Copy files then remove from repo
foreach ($rel in $items) {
  $src = Join-Path $root $rel
  if (Test-Path $src) {
    $dst = Join-Path $destRoot $rel
    Ensure-Dir (Split-Path $dst -Parent)
    Copy-Item -LiteralPath $src -Destination $dst -Force
    "  Copied: $rel -> local_ai_private" | Out-File -FilePath $logPath -Encoding utf8 -Append

    if (-not $NoGit) {
      try {
        Push-Location $root
        & git rm -f -- $rel 2>$null | Out-Null
      } catch { }
      finally { Pop-Location }
    }

    # Remove original from working tree if still present
    if (Test-Path $src) { Remove-Item -LiteralPath $src -Force }
  }
}

# Handle directories (e.g., .claude)
foreach ($drel in $dirs) {
  $dsrc = Join-Path $root $drel
  if (Test-Path $dsrc) {
    $ddst = Join-Path $destRoot $drel
    Ensure-Dir (Split-Path $ddst -Parent)
    Copy-Item -LiteralPath $dsrc -Destination $ddst -Recurse -Force
    "  Copied dir: $drel -> local_ai_private" | Out-File -FilePath $logPath -Encoding utf8 -Append

    if (-not $NoGit) {
      try {
        Push-Location $root
        & git rm -r -f -- $drel 2>$null | Out-Null
      } catch { }
      finally { Pop-Location }
    }

    if (Test-Path $dsrc) { Remove-Item -LiteralPath $dsrc -Recurse -Force }
  }
}

"[$timestamp] Migration finished" | Out-File -FilePath $logPath -Encoding utf8 -Append
Write-Host "[OK] AI/TODO artifacts moved to local_ai_private/ and removed from repo (staged deletions)."