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
    [switch] $IncludeRuntimeDb,
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
    Write-Host "  Instalador Windows: ativado por padrao; use -SkipInstaller para desativar"
    Write-Host ""
    Write-Host "Opcoes uteis:"
    Write-Host "  -DryRun              mostra plano sem build/pacote"
    Write-Host "  -Yes                 executa sem prompt"
    Write-Host "  -Target all          Windows local + Debian via WSL"
    Write-Host "  -AllowMissingRemote  em -Target all, pula Debian se WSL nao existir"
    Write-Host "  -IncludeRuntimeDb    inclui data\ssas.db no build Windows PyInstaller"
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

    $values = @()
    foreach ($item in $Items) {
        foreach ($token in ($item -split ",")) {
            $value = $token.Trim().ToLowerInvariant()
            if (-not [string]::IsNullOrWhiteSpace($value)) {
                $values += $value
            }
        }
    }
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

function Invoke-WindowsRelease {
    param(
        [Parameter(Mandatory = $true)] [string] $RepoRoot,
        [Parameter(Mandatory = $true)] [string] $BackendCsv
    )

    Assert-WindowsReleaseHost
    Initialize-WindowsBuildExtra $RepoRoot $BackendCsv
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
    if ($IncludeRuntimeDb) {
        $releaseArgs += "-IncludeRuntimeDb"
    }
    & powershell @releaseArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Release Windows falhou."
    }
}

function Initialize-WindowsBuildExtra {
    param(
        [Parameter(Mandatory = $true)] [string] $RepoRoot,
        [Parameter(Mandatory = $true)] [string] $BackendCsv
    )

    $moduleByBackend = @{
        nuitka = "nuitka"
        pyinstaller = "PyInstaller"
    }
    $modules = @()
    $needsPyoxidizer = $false
    foreach ($backend in ($BackendCsv -split ",")) {
        $value = $backend.Trim().ToLowerInvariant()
        if ($moduleByBackend.ContainsKey($value)) {
            $moduleName = $moduleByBackend[$value]
            if ($modules -notcontains $moduleName) {
                $modules += $moduleName
            }
            continue
        }
        if ($value -eq "pyoxidizer") {
            $needsPyoxidizer = $true
            continue
        }
        if (-not [string]::IsNullOrWhiteSpace($value)) {
            throw "Backend Windows invalido: $value. Use nuitka, pyinstaller, pyoxidizer ou combinacoes separadas por virgula."
        }
    }
    if ($modules.Count -eq 0 -and -not $needsPyoxidizer) {
        return
    }
    if (-not (Get-Command "uv" -ErrorAction SilentlyContinue)) {
        throw "uv nao encontrado no PATH. Instale uv ou abra um shell com uv disponivel antes do release."
    }

    if ($modules.Count -gt 0) {
        $imports = ($modules | ForEach-Object { "import $_" }) -join "; "
        $uvOutput = @()
        Push-Location $RepoRoot
        try {
            $uvOutput = & uv @(
                "run",
                "--python",
                "3.13",
                "--extra",
                "build",
                "python",
                "-c",
                $imports
            ) 2>&1
            if ($LASTEXITCODE -ne 0) {
                $uvDetails = ($uvOutput | Out-String -Width 240).Trim()
                if ([string]::IsNullOrWhiteSpace($uvDetails)) {
                    $uvDetails = "uv nao retornou stdout/stderr."
                }
                if ($uvDetails.Length -gt 4000) {
                    $uvDetails = $uvDetails.Substring($uvDetails.Length - 4000)
                }
                throw "uv run --extra build falhou. Output: $uvDetails"
            }
        } catch {
            $detail = $_.Exception.Message
            $uvDetails = ($uvOutput | Out-String -Width 240).Trim()
            if (-not [string]::IsNullOrWhiteSpace($uvDetails) -and -not $detail.Contains($uvDetails)) {
                if ($uvDetails.Length -gt 4000) {
                    $uvDetails = $uvDetails.Substring($uvDetails.Length - 4000)
                }
                $detail = "$detail Output: $uvDetails"
            }
            throw "Dependencias de build ausentes ou indisponiveis para ${BackendCsv}. Use 'uv sync --extra build' ou verifique a rede/cache do uv. Detalhe: $detail"
        } finally {
            Pop-Location
        }
    }
    if ($needsPyoxidizer) {
        $pyoxidizerPackage = if ($env:SSA_PYOXIDIZER_UV_PACKAGE) { $env:SSA_PYOXIDIZER_UV_PACKAGE } else { "pyoxidizer==0.24.0" }
        $pyoxidizerOutput = & uv @(
            "tool",
            "run",
            "--python",
            "3.13",
            "--from",
            $pyoxidizerPackage,
            "pyoxidizer",
            "--version"
        ) 2>&1
        if ($LASTEXITCODE -ne 0) {
            $detail = ($pyoxidizerOutput | Out-String -Width 240).Trim()
            throw "PyOxidizer indisponivel via uv tool: $pyoxidizerPackage. Detalhe: $detail"
        }
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
    if ($WslDistro -notmatch "^[A-Za-z0-9_.-]+$") {
        throw "Nome de distro WSL invalido: $WslDistro"
    }
    if ($BackendCsv -notmatch "^[A-Za-z0-9_.-]+(,[A-Za-z0-9_.-]+)*$") {
        throw "Backend Debian invalido: $BackendCsv"
    }
    if ($PackageCsv -notmatch "^[A-Za-z0-9_.-]+(,[A-Za-z0-9_.-]+)*$") {
        throw "Pacote Debian invalido: $PackageCsv"
    }

    $repoRootWsl = ConvertTo-WslPath $RepoRoot
    $scriptWsl = "$repoRootWsl/dev_env/build/release_debian.sh"
    $releaseArgs = @("-d", $WslDistro, "--", "bash", $scriptWsl, "--backend", $BackendCsv, "--package", $PackageCsv)
    if ($Yes) {
        $releaseArgs += "-y"
    }
    if ($DryRun) {
        $releaseArgs += "--dry-run"
    }

    & wsl @releaseArgs
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
