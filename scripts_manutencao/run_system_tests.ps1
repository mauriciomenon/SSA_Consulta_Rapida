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

    # Executa testes automatizados integrados (gera relatorio em docs_saida)
    Write-Header "Executando testes automatizados (tests/automated_system_tests.py)"
    $py = Get-Command python -ErrorAction Stop
    $testScript = Join-Path 'tests' 'automated_system_tests.py'
    $outputLog = Join-Path 'docs_saida' 'last_system_test_stdout.txt'
    $proc = Start-Process $py.Source -ArgumentList $testScript -NoNewWindow -PassThru -Wait -RedirectStandardOutput $outputLog

    # Captura o arquivo de relatorio mais recente
    $reportPattern = Join-Path 'docs_saida' 'automated_tests_report_*.md'
    $report = Get-ChildItem $reportPattern -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($null -ne $report) {
        Write-Host "Relatorio: $($report.FullName)" -ForegroundColor Green
        if ($OpenReport) {
            Write-Header "Abrindo relatorio"
            Start-Process $report.FullName | Out-Null
        }
    } else {
        Write-Warning "Relatorio nao encontrado. Verifique logs em $(Join-Path 'docs_saida' 'last_system_test_stdout.txt')"
    }

    if ($proc.ExitCode -eq 0) {
        Write-Host "Testes concluidos com sucesso." -ForegroundColor Green
        exit 0
    } else {
        Write-Warning "Alguns testes falharam. Consulte o relatorio."
        exit 1
    }
}
catch {
    Write-Error $_
    exit 1
}

