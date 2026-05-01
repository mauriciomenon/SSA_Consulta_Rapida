param(
    [ValidateSet("pyinstaller", "nuitka", "pyoxidizer", "all")]
    [string[]] $Backend = @("all"),
    [ValidateSet("deb", "appimage", "tar", "all")]
    [string[]] $DebianPackage = @("all"),
    [string] $WslDistro = "Debian",
    [switch] $SkipWindows,
    [switch] $SkipDebian,
    [switch] $DryRun,
    [switch] $Yes
)

Set-StrictMode -Version 3.0
$ErrorActionPreference = "Stop"

function Resolve-RepoRoot {
    $root = (git rev-parse --show-toplevel).Trim()
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($root)) {
        throw "Nao foi possivel localizar a raiz git."
    }
    return (Resolve-Path $root).Path
}

function Assert-Tool {
    param([Parameter(Mandatory = $true)] [string] $Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Ferramenta obrigatoria ausente: $Name"
    }
}

function ConvertTo-WslPath {
    param([Parameter(Mandatory = $true)] [string] $Path)
    $resolved = (Resolve-Path $Path).Path
    if ($resolved -notmatch "^[A-Za-z]:\\") {
        throw "Caminho Windows absoluto esperado: $resolved"
    }
    $drive = $resolved.Substring(0, 1).ToLowerInvariant()
    $tail = $resolved.Substring(2).Replace("\", "/")
    return "/mnt/$drive$tail"
}

function Join-Csv {
    param([Parameter(Mandatory = $true)] [string[]] $Items)
    if ($Items -contains "all") {
        return "all"
    }
    return (($Items | Select-Object -Unique) -join ",")
}

Assert-Tool "git"
Assert-Tool "wsl"

$repoRoot = Resolve-RepoRoot
$repoRootWsl = ConvertTo-WslPath $repoRoot
$backendCsv = Join-Csv $Backend
$packageCsv = Join-Csv $DebianPackage

if (-not $Yes) {
    Write-Host "Repo: $repoRoot"
    Write-Host "WSL repo: $repoRootWsl"
    Write-Host "Backends: $backendCsv"
    Write-Host "Debian packages: $packageCsv"
    $confirm = Read-Host "Continuar release local? [s/N]"
    if ($confirm.ToLowerInvariant() -ne "s") {
        throw "Operacao cancelada pelo usuario."
    }
}

if (-not $SkipWindows) {
    $windowsArgs = @(
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        (Join-Path $repoRoot "dev_env\build\release_windows.ps1"),
        "-Backend",
        $backendCsv,
        "-Yes"
    )
    if ($DryRun) {
        $windowsArgs += "-DryRun"
    }
    & powershell @windowsArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Release Windows falhou."
    }
}

if (-not $SkipDebian) {
    $debianArgs = @(
        "-d",
        $WslDistro,
        "--",
        "bash",
        "-lc",
        "cd '$repoRootWsl' && bash dev_env/build/release_debian.sh --backend '$backendCsv' --package '$packageCsv' -y$(if ($DryRun) { ' --dry-run' } else { '' })"
    )
    & wsl @debianArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Release Debian falhou."
    }
}

Write-Host "Release local concluido."
