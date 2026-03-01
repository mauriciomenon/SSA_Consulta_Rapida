# Script de Reorganização Local - local_ai_private/
# Organiza arquivos migrados em estrutura lógica por categoria

$ErrorActionPreference = 'Stop'
$baseDir = Join-Path $PSScriptRoot ".." "local_ai_private"

Write-Host "  REORGANIZANDO ESTRUTURA LOCAL (NÃO VERSIONADA)" -ForegroundColor Cyan
Write-Host "=" * 70

# 1. Criar estrutura de diretórios
Write-Host "`nDIR Criando estrutura de diretórios..." -ForegroundColor Yellow

$estrutura = @(
    "01_ai_sessions/claude",
    "01_ai_sessions/gemini",
    "01_ai_sessions/copilot",
    "01_ai_sessions/outros",
    "02_checklists_planos/checklists",
    "02_checklists_planos/planos",
    "02_checklists_planos/proximos_passos",
    "03_relatorios_analises/performance",
    "03_relatorios_analises/qualidade",
    "03_relatorios_analises/consolidacao",
    "04_historico_sessions/session_logs",
    "04_historico_sessions/recovery",
    "04_historico_sessions/security",
    "05_scripts_pessoais/testes",
    "05_scripts_pessoais/manutencao",
    "05_scripts_pessoais/deprecated",
    "06_backups_configs/vscode",
    "06_backups_configs/emoji_backups",
    "06_backups_configs/outros",
    "00_backup_pre_reorg"
)

foreach ($dir in $estrutura) {
    $fullPath = Join-Path $baseDir $dir
    if (-not (Test-Path $fullPath)) {
        New-Item -ItemType Directory -Path $fullPath -Force | Out-Null
        Write-Host "   Criado: $dir" -ForegroundColor Green
    }
}

# 2. Criar backup antes de reorganizar
Write-Host "`n Criando backup pré-reorganização..." -ForegroundColor Yellow
$backupDir = Join-Path $baseDir "00_backup_pre_reorg"
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupSubDir = Join-Path $backupDir "backup_$timestamp"
New-Item -ItemType Directory -Path $backupSubDir -Force | Out-Null

Get-ChildItem $baseDir -File | ForEach-Object {
    Copy-Item $_.FullName -Destination $backupSubDir -Force
    Write-Host "   Backup: $($_.Name)" -ForegroundColor Gray
}

# 3. Definir regras de categorização
$regras = @{
    "01_ai_sessions/claude" = @("*claude*.txt", "*claude*.md", "temp_claude*")
    "01_ai_sessions/gemini" = @("*gemini*.md", "*gemini*.html", "gemini.md")
    "01_ai_sessions/copilot" = @("*copilot*.md", "*copilot*.json")
    
    "02_checklists_planos/checklists" = @("CHECKLIST_*.md")
    "02_checklists_planos/planos" = @("PLANOS_*.md", "PLANEJAMENTO*.md", "*ROADMAP*.md")
    "02_checklists_planos/proximos_passos" = @("PROXIMOS_PASSOS*.md", "NEXT_STEPS*.md", "*ORDENS*.md")
    
    "03_relatorios_analises/performance" = @("*PERFORMANCE*.md", "ANALISE_PERFORMANCE*.md")
    "03_relatorios_analises/qualidade" = @("*avaliacao*.md", "*avaliacao*.html", "*QUALITY*.md")
    "03_relatorios_analises/consolidacao" = @("RELATORIO*.md", "RESUMO*.md", "*CONSOLIDACAO*.md")
    
    "04_historico_sessions/session_logs" = @("SESSION_*.md", "LOG_*.md")
    "04_historico_sessions/security" = @("SECRET_*.md", "*SECURITY*.md")
    
    "05_scripts_pessoais/testes" = @("test_*.ps1", "test_*.py", "*_test.ps1", "meu_*.ps1")
    "05_scripts_pessoais/manutencao" = @("fix_*.py", "cleanup*.py", "verify*.py")
}

# 4. Processar movimentações
Write-Host "`nRUN Movendo arquivos para categorias apropriadas..." -ForegroundColor Yellow
$log = @()
$movedCount = 0

foreach ($categoria in $regras.Keys) {
    $destino = Join-Path $baseDir $categoria
    $patterns = $regras[$categoria]
    
    foreach ($pattern in $patterns) {
        $arquivos = Get-ChildItem $baseDir -File -Filter $pattern -ErrorAction SilentlyContinue
        
        foreach ($arquivo in $arquivos) {
            # Pular se já está na pasta de backup
            if ($arquivo.DirectoryName -like "*00_backup_pre_reorg*") {
                continue
            }
            
            # Pular se já está na estrutura organizada
            $relativePath = $arquivo.DirectoryName.Replace($baseDir, "").TrimStart("\")
            if ($relativePath -match "^\d{2}_") {
                continue
            }
            
            $novoLocal = Join-Path $destino $arquivo.Name
            
            # Se arquivo já existe no destino, adicionar sufixo
            if (Test-Path $novoLocal) {
                $base = [System.IO.Path]::GetFileNameWithoutExtension($arquivo.Name)
                $ext = $arquivo.Extension
                $i = 1
                while (Test-Path $novoLocal) {
                    $novoLocal = Join-Path $destino "$base`_$i$ext"
                    $i++
                }
            }
            
            Move-Item $arquivo.FullName -Destination $novoLocal -Force
            $logEntry = "$($arquivo.Name) → $categoria"
            $log += $logEntry
            Write-Host "   $logEntry" -ForegroundColor Green
            $movedCount++
        }
    }
}

# 5. Mover diretórios especiais
Write-Host "`nIN Movendo diretórios especiais..." -ForegroundColor Yellow

# .claude → 01_ai_sessions/copilot/  (ou manter separado)
$claudeDir = Join-Path $baseDir ".claude"
if (Test-Path $claudeDir) {
    $destClaude = Join-Path $baseDir "01_ai_sessions\copilot\.claude"
    if (-not (Test-Path (Split-Path $destClaude))) {
        New-Item -ItemType Directory -Path (Split-Path $destClaude) -Force | Out-Null
    }
    Move-Item $claudeDir -Destination $destClaude -Force
    Write-Host "   .claude → 01_ai_sessions/copilot/" -ForegroundColor Green
    $log += ".claude/ → 01_ai_sessions/copilot/"
}

# .github (copilot-instructions) → 01_ai_sessions/copilot/
$githubDir = Join-Path $baseDir ".github"
if (Test-Path $githubDir) {
    $destGithub = Join-Path $baseDir "01_ai_sessions\copilot\.github"
    if (-not (Test-Path (Split-Path $destGithub))) {
        New-Item -ItemType Directory -Path (Split-Path $destGithub) -Force | Out-Null
    }
    Move-Item $githubDir -Destination $destGithub -Force
    Write-Host "   .github → 01_ai_sessions/copilot/" -ForegroundColor Green
    $log += ".github/ → 01_ai_sessions/copilot/"
}

# docs/ → categorizar por tipo
$docsDir = Join-Path $baseDir "docs"
if (Test-Path $docsDir) {
    Get-ChildItem $docsDir -File | ForEach-Object {
        $arquivo = $_
        $moved = $false
        
        # Tentar categorizar cada arquivo do docs/
        foreach ($categoria in $regras.Keys) {
            $patterns = $regras[$categoria]
            foreach ($pattern in $patterns) {
                if ($arquivo.Name -like $pattern) {
                    $destino = Join-Path $baseDir $categoria
                    $novoLocal = Join-Path $destino $arquivo.Name
                    
                    if (Test-Path $novoLocal) {
                        $base = [System.IO.Path]::GetFileNameWithoutExtension($arquivo.Name)
                        $ext = $arquivo.Extension
                        $i = 1
                        while (Test-Path $novoLocal) {
                            $novoLocal = Join-Path $destino "$base`_$i$ext"
                            $i++
                        }
                    }
                    
                    Move-Item $arquivo.FullName -Destination $novoLocal -Force
                    Write-Host "   docs/$($arquivo.Name) → $categoria" -ForegroundColor Green
                    $log += "docs/$($arquivo.Name) → $categoria"
                    $moved = $true
                    $movedCount++
                    break
                }
            }
            if ($moved) { break }
        }
        
        # Se não categorizou, mover para 04_historico_sessions/session_logs
        if (-not $moved) {
            $destino = Join-Path $baseDir "04_historico_sessions\session_logs"
            $novoLocal = Join-Path $destino $arquivo.Name
            Move-Item $arquivo.FullName -Destination $novoLocal -Force
            Write-Host "   docs/$($arquivo.Name) → 04_historico_sessions/session_logs (fallback)" -ForegroundColor Yellow
            $log += "docs/$($arquivo.Name) → 04_historico_sessions/session_logs"
            $movedCount++
        }
    }
    
    # Remover diretório docs/ se vazio
    if ((Get-ChildItem $docsDir -Recurse).Count -eq 0) {
        Remove-Item $docsDir -Force -Recurse
        Write-Host "   Removido diretório docs/ vazio" -ForegroundColor Gray
    }
}

# 6. Gerar log de reorganização
Write-Host "`n Gerando log de reorganização..." -ForegroundColor Yellow
$logPath = Join-Path $baseDir "REORGANIZATION_LOG_$timestamp.txt"
$logContent = @"
=== LOG DE REORGANIZAÇÃO LOCAL ===
Data: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
Arquivos movidos: $movedCount

Estrutura criada:
$(($estrutura | ForEach-Object { "  - $_" }) -join "`n")

Movimentações realizadas:
$(($log | ForEach-Object { "  • $_" }) -join "`n")

Backup pré-reorganização:
  Localização: 00_backup_pre_reorg/backup_$timestamp/

Próximos passos:
  1. Revisar estrutura: Verificar se todos os arquivos estão em categorias corretas
  2. Adicionar READMEs: Considerar criar README.md em cada subpasta com contexto
  3. Limpar backups antigos: Após confirmar que está tudo OK, limpar 00_backup_pre_reorg/ antigos

Estrutura completa documentada em: README_ESTRUTURA.md
"@

$logContent | Out-File -FilePath $logPath -Encoding UTF8
Write-Host "   Log salvo: $logPath" -ForegroundColor Green

# 7. Resumo final
Write-Host "`nOK REORGANIZAÇÃO CONCLUÍDA!" -ForegroundColor Green
Write-Host "=" * 70
Write-Host "INFO Estatísticas:" -ForegroundColor Cyan
Write-Host "  • Arquivos movidos: $movedCount" -ForegroundColor White
Write-Host "  • Backup criado em: 00_backup_pre_reorg/backup_$timestamp/" -ForegroundColor White
Write-Host "  • Log detalhado: REORGANIZATION_LOG_$timestamp.txt" -ForegroundColor White
Write-Host "`n Consulte README_ESTRUTURA.md para detalhes da estrutura" -ForegroundColor Yellow
Write-Host ""

# 8. Listar estrutura final
Write-Host "  Estrutura Final:" -ForegroundColor Cyan
Get-ChildItem $baseDir -Directory | Where-Object { $_.Name -match "^\d{2}_" } | ForEach-Object {
    $count = (Get-ChildItem $_.FullName -Recurse -File).Count
    Write-Host "  $($_.Name): $count arquivo(s)" -ForegroundColor White
}

Write-Host "`n Tudo pronto! Seus arquivos locais agora estão organizados." -ForegroundColor Green
