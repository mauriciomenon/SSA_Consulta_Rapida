# Setup both pre-commit and pre-push hooks for large file checks
param()

$hooks = Join-Path (git rev-parse --git-dir) 'hooks'
if (-not (Test-Path $hooks)) { New-Item -ItemType Directory -Path $hooks | Out-Null }

Copy-Item scripts/pre-commit-size-check.ps1 "$hooks/pre-commit" -Force
Copy-Item scripts/pre-push-large-object-check.ps1 "$hooks/pre-push" -Force

git config core.hooksPath $hooks

Write-Host "Hooks instalados em: $hooks" -ForegroundColor Green
