[CmdletBinding(PositionalBinding = $false)]
param(
    [string] $Target = "windows",
    [string[]] $Backend = @(),
    [string[]] $DebianPackage = @(),
    [string] $WslDistro = "Debian",
    [switch] $Yes,
    [switch] $DryRun,
    [switch] $AllowMissingRemote,
    [switch] $SkipInstaller,
    [switch] $Help
)

Set-StrictMode -Version 3.0
$ErrorActionPreference = "Stop"

$DefaultBackend = "nuitka"
$DefaultDebianPackage = "deb"

function Show-Usage {
    Write-Host "Uso:"
    Write-Host "  .\release.ps1"
    Write-Host "  .\release.ps1 -Target windows"
    Write-Host "  .\release.ps1 -Target debian"
    Write-Host "  .\release.ps1 -Target all -Yes"
    Write-Host ""
    Write-Host "Defaults:"
    Write-Host "  Target: windows"
    Write-Host "  Backend Windows/Debian: nuitka"
    Write-Host "  Pacote Debian: deb"
    Write-Host "  Instalador Windows: obrigatorio, exceto com -SkipInstaller"
    Write-Host ""
    Write-Host "Opcoes uteis:"
    Write-Host "  -DryRun              mostra plano sem build/pacote"
    Write-Host "  -Yes                 executa sem prompt"
    Write-Host "  -Target all          Windows local + Debian via WSL"
    Write-Host "  -AllowMissingRemote  em -Target all, pula Debian se WSL nao existir"
}

function Resolve-RepoRoot {
    $root = (git rev-parse --show-toplevel).Trim()
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($root)) {
        throw "Nao foi possivel localizar a raiz git."
    }
    return (Resolve-Path $root).Path
}

function Join-ReleaseCsv {
    param(
        [string[]] $Items,
        [Parameter(Mandatory = $true)] [string] $DefaultValue
    )

    $values = @(
    foreach ($item in $Items) {
        foreach ($token in ($item -split ",")) {
            $value = $token.Trim().ToLowerInvariant()
            if (-not [string]::IsNullOrWhiteSpace($value)) {
                $value
            }
        }
    }
    )
    if ($values.Count -eq 0) {
        return $DefaultValue
    }
    return (($values | Select-Object -Unique) -join ",")
}

function Normalize-Target {
    param([Parameter(Mandatory = $true)] [string] $RawTarget)

    $value = $RawTarget.Trim().ToLowerInvariant()
    if ($value -notin @("windows", "debian", "all")) {
        throw "Target invalido: $RawTarget. Use windows, debian ou all."
    }
    return $value
}

function Assert-WindowsReleaseHost {
    if ([System.Environment]::OSVersion.Platform -ne [System.PlatformID]::Win32NT) {
        throw "Release Windows deve rodar em Windows ou VM Windows. Host atual: $([System.Environment]::OSVersion.Platform)."
    }
}

function ConvertTo-WslPath {
    param([Parameter(Mandatory = $true)] [string] $Path)

    $resolved = (Resolve-Path $Path).Path
    if ($resolved -notmatch "^[A-Za-z]:\\") {
        throw "Caminho Windows absoluto esperado para WSL: $resolved"
    }
    $drive = $resolved.Substring(0, 1).ToLowerInvariant()
    $tail = $resolved.Substring(2).Replace("\", "/")
    return "/mnt/$drive$tail"
}

function ConvertTo-BashSingleQuoted {
    param([Parameter(Mandatory = $true)] [string] $Value)

    $singleQuote = [char]39
    $escaped = $Value.Replace([string] $singleQuote, "$singleQuote\$singleQuote$singleQuote")
    return "$singleQuote$escaped$singleQuote"
}

function Invoke-WindowsRelease {
    param(
        [Parameter(Mandatory = $true)] [string] $RepoRoot,
        [Parameter(Mandatory = $true)] [string] $BackendCsv
    )

    Assert-WindowsReleaseHost
    Assert-WindowsBuildExtra $RepoRoot $BackendCsv
    $script = Join-Path $RepoRoot "dev_env\build\release_windows.ps1"
    $releaseArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $script, "-Backend", $BackendCsv)
    if ($Yes) {
        $releaseArgs += "-Yes"
    }
    if ($DryRun) {
        $releaseArgs += "-DryRun"
    }
    if ($SkipInstaller) {
        $releaseArgs += "-SkipInstaller"
    }
    & powershell @releaseArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Release Windows falhou."
    }
}

function Assert-WindowsBuildExtra {
    param(
        [Parameter(Mandatory = $true)] [string] $RepoRoot,
        [Parameter(Mandatory = $true)] [string] $BackendCsv
    )

    $modules = @()
    foreach ($backend in ($BackendCsv -split ",")) {
        $value = $backend.Trim().ToLowerInvariant()
        if ($value -eq "nuitka" -and $modules -notcontains "nuitka") {
            $modules += "nuitka"
        }
        if ($value -eq "pyinstaller" -and $modules -notcontains "PyInstaller") {
            $modules += "PyInstaller"
        }
    }
    if ($modules.Count -eq 0) {
        return
    }

    $imports = ($modules | ForEach-Object { "import $_" }) -join "; "
    Push-Location $RepoRoot
    try {
        & uv @(
            "run",
            "--python",
            "3.13",
            "--extra",
            "build",
            "python",
            "-c",
            $imports
        ) | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "uv run --extra build falhou."
        }
    } catch {
        throw "Dependencias de build ausentes ou indisponiveis para ${BackendCsv}. Use 'uv sync --extra build' ou verifique a rede/cache do uv. Detalhe: $($_.Exception.Message)"
    } finally {
        Pop-Location
    }
}

function Invoke-DebianReleaseViaWsl {
    param(
        [Parameter(Mandatory = $true)] [string] $RepoRoot,
        [Parameter(Mandatory = $true)] [string] $BackendCsv,
        [Parameter(Mandatory = $true)] [string] $PackageCsv
    )

    if (-not (Get-Command "wsl" -ErrorAction SilentlyContinue)) {
        throw "WSL nao encontrado. Instale WSL ou use -AllowMissingRemote com -Target all."
    }

    $repoRootWsl = ConvertTo-WslPath $RepoRoot
    $repoRootWslQuoted = ConvertTo-BashSingleQuoted $repoRootWsl
    $backendQuoted = ConvertTo-BashSingleQuoted $BackendCsv
    $packageQuoted = ConvertTo-BashSingleQuoted $PackageCsv
    $dryRunFlag = if ($DryRun) { " --dry-run" } else { "" }
    $yesFlag = if ($Yes) { " -y" } else { "" }
    $command = "cd $repoRootWslQuoted && bash dev_env/build/release_debian.sh --backend $backendQuoted --package $packageQuoted$yesFlag$dryRunFlag"

    & wsl -d $WslDistro -- bash -lc $command
    if ($LASTEXITCODE -ne 0) {
        throw "Release Debian via WSL falhou."
    }
}

if ($Help) {
    Show-Usage
    return
}

$targetName = Normalize-Target $Target
$repoRoot = Resolve-RepoRoot
$backendCsv = Join-ReleaseCsv $Backend $DefaultBackend
$packageCsv = Join-ReleaseCsv $DebianPackage $DefaultDebianPackage

Write-Host "Release target: $targetName"
Write-Host "Backend: $backendCsv"
if ($targetName -in @("debian", "all")) {
    Write-Host "Pacote Debian: $packageCsv"
}

if ($targetName -in @("windows", "all")) {
    Invoke-WindowsRelease $repoRoot $backendCsv
}

if ($targetName -in @("debian", "all")) {
    try {
        Invoke-DebianReleaseViaWsl $repoRoot $backendCsv $packageCsv
    } catch {
        if ($targetName -eq "all" -and $AllowMissingRemote) {
            Write-Host "Debian via WSL pulado: $($_.Exception.Message)"
        } else {
            throw
        }
    }
}

Write-Host "Release concluido."
