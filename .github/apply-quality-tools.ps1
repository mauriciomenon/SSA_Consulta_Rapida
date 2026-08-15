#!/usr/bin/env pwsh
# Script para aplicar configuracoes de quality/security em todos repos

param(
    [string]$GithubOrg = "mauriciomenon",
    [string]$SnykOrgId = "1c43a760-bde3-4178-b0ef-2885be92ce3d",
    [switch]$DryRun
)

$repos = @(
    "SSA_Consulta_Rapida"
    # Adicione outros repos aqui
)

$templatesDir = ".github"

foreach ($repo in $repos) {
    Write-Host "==> Configurando: $repo" -ForegroundColor Cyan
    $repoPath = Join-Path $env:USERPROFILE "git\$repo"
    if (-not (Test-Path $repoPath)) {
        Write-Warning "Repo nao encontrado: $repoPath"
        continue
    }

    Push-Location $repoPath
    try {
        # Cria .github se nao existir
        $githubDir = ".github"
        if (-not (Test-Path $githubDir)) {
            New-Item -ItemType Directory -Path $githubDir | Out-Null
        }
        $workflowsDir = Join-Path $githubDir "workflows"
        if (-not (Test-Path $workflowsDir)) {
            New-Item -ItemType Directory -Path $workflowsDir | Out-Null
        }
        # Copia workflows
        Write-Host "  - Workflows..."
        Copy-Item "$templatesDir\workflows\*.yml" $workflowsDir -Force

        # Copia configs
        Write-Host "  - Dependabot..."
        Copy-Item "$templatesDir\dependabot-template.yml" "$githubDir\dependabot.yml" -Force
        Write-Host "  - SonarCloud..."
        if (-not (Test-Path "sonar-project.properties")) {
            $sonarTemplate = Get-Content "$templatesDir\sonar-template.properties" -Raw
            $sonarConfig = $sonarTemplate -replace "NOME_DO_PROJETO", $repo
            Set-Content "sonar-project.properties" $sonarConfig
        }
        # Configs opcionais
        Write-Host "  - CodeFactor/Codacy..."
        if (-not (Test-Path ".codefactor")) {
            @"
languages:
  Python: true

exclude:
  - "tests/**"
  - "build/**"
  - "dist/**"
  - "**/__pycache__/**"
"@ | Set-Content ".codefactor"
        }
        if (-not (Test-Path ".codacy.yml")) {
            @"
engines:
  pylint:
    enabled: true
  bandit:
    enabled: true
  prospector:
    enabled: true

exclude_paths:
  - "tests/**"
  - "build/**"
  - "dist/**"
  - "**/__pycache__/**"
"@ | Set-Content ".codacy.yml"
        }
        if (-not $DryRun) {
            Write-Host "  - Commit & Push..." -ForegroundColor Green
            git add .
            git commit -m "ci: add code quality and security automation"
            git push origin main
        } else {
            Write-Host "  - [DRY RUN] Mudancas preparadas" -ForegroundColor Yellow
        }
    } catch {
        Write-Error "Erro em ${repo}: $_"
    } finally {
        Pop-Location
    }
}

Write-Host "`n==> Concluido!" -ForegroundColor Green
Write-Host "`nProximos passos:"
Write-Host "1. Configure secrets SONAR_TOKEN e SNYK_TOKEN em cada repo"
Write-Host "2. Habilite workflows em Settings > Actions"
Write-Host "3. Conecte repos no SonarCloud e Snyk dashboards"
