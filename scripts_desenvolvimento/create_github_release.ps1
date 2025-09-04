param(
  [string]$Tag = "v3.10",
  [string]$Repo = "mauriciomenon/SSA_Consulta_Rapida",
  [switch]$Draft
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent
$notes = Join-Path $root 'docs_saida/GITHUB_RELEASE_' + $Tag + '.md'
if (-not (Test-Path $notes)) {
  # fallback para v3.10
  $notes = Join-Path $root 'docs_saida/GITHUB_RELEASE_v3.10.md'
}
if (-not (Test-Path $notes)) {
  Write-Error "Arquivo de notas não encontrado: $notes"
}

function Has-GhCli { (Get-Command gh -ErrorAction SilentlyContinue) -ne $null }

if (Has-GhCli) {
  Write-Host "Usando GitHub CLI (gh) para criar release" -ForegroundColor Cyan
  $args = @('release','create',$Tag,'--title',"SSA Consulta Rápida $Tag",'--notes-file',$notes)
  if ($Draft) { $args += '--draft' }
  & gh @args
  exit $LASTEXITCODE
}

Write-Warning "gh CLI não encontrado. Crie manualmente o release usando o arquivo: $notes"
Write-Host "Link: https://github.com/$Repo/releases/new?tag=$Tag&title=$Tag" -ForegroundColor Yellow
