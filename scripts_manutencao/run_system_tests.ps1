Param(
    [switch]$OpenReport
)

$ErrorActionPreference = 'Stop'

function Write-Header($text) {
    Write-Host "=== $text ===" -ForegroundColor Cyan
}

try {
    Write-Header "Preparando ambiente para testes do sistema"

    # Seta Qt em offscreen para evitar erros de display em ambientes headless/CI
    $env:QT_QPA_PLATFORM = 'offscreen'

    # Executa testes automatizados integrados (gera relatório em docs_saida)
    Write-Header "Executando testes automatizados (tests/automated_system_tests.py)"
    $py = Get-Command python -ErrorAction Stop
    $proc = Start-Process $py.Source -ArgumentList 'tests/automated_system_tests.py' -NoNewWindow -PassThru -Wait -RedirectStandardOutput 'docs_saida/last_system_test_stdout.txt'

    # Captura o arquivo de relatório mais recente
    $report = Get-ChildItem docs_saida\automated_tests_report_*.md -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($null -ne $report) {
        Write-Host "Relatório: $($report.FullName)" -ForegroundColor Green
        if ($OpenReport) {
            Write-Header "Abrindo relatório"
            Start-Process $report.FullName | Out-Null
        }
    } else {
        Write-Warning "Relatório não encontrado. Verifique logs em docs_saida/last_system_test_stdout.txt"
    }

    if ($proc.ExitCode -eq 0) {
        Write-Host "Testes concluídos com sucesso." -ForegroundColor Green
        exit 0
    } else {
        Write-Warning "Alguns testes falharam. Consulte o relatório."
        exit 1
    }
}
catch {
    Write-Error $_
    exit 1
}

