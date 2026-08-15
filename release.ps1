[CmdletBinding(PositionalBinding = $false)]
param(
    [string] $Target = "windows",
    [string[]] $Backend = @(),
    [switch] $Yes,
    [switch] $DryRun,
    [switch] $SkipInstaller,
    [switch] $IncludeRuntimeDb,
    [switch] $Help
)

Set-StrictMode -Version 3.0
$ErrorActionPreference = "Stop"

$DefaultBackend = "nuitka"

function Show-Usage {
    Write-Host "Uso:"
    Write-Host "  .\release.ps1"
    Write-Host "  .\release.ps1 -Target windows"
    Write-Host ""
    Write-Host "Defaults:"
    Write-Host "  Target: windows"
    Write-Host "  Backend Windows: nuitka"
    Write-Host "  Instalador Windows: ativado por padrao; use -SkipInstaller para desativar"
    Write-Host ""
    Write-Host "Opcoes uteis:"
    Write-Host "  -DryRun              mostra plano sem build/pacote"
    Write-Host "  -Yes                 executa sem prompt"
    Write-Host "  -IncludeRuntimeDb    inclui data\ssas.db no build Windows PyInstaller"
    Write-Host "  Debian deve usar ./release.sh em clone Linux nativo; WSL fica restrito ao CodeRabbit."
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
    if ($value -ne "windows") {
        throw "Target invalido no wrapper Windows: $RawTarget. Use windows; Debian deve rodar via ./release.sh em clone Linux nativo."
    }
    return $value
}

function Assert-WindowsReleaseHost {
    if ([System.Environment]::OSVersion.Platform -ne [System.PlatformID]::Win32NT) {
        throw "Release Windows deve rodar em Windows ou VM Windows. Host atual: $([System.Environment]::OSVersion.Platform)."
    }
}

function Invoke-WindowsRelease {
    param(
        [Parameter(Mandatory = $true)] [string] $RepoRoot,
        [Parameter(Mandatory = $true)] [string] $BackendCsv
    )

    Assert-WindowsReleaseHost
    if (-not $DryRun) {
        Initialize-WindowsBuildExtra $RepoRoot $BackendCsv
    }
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

if ($Help) {
    Show-Usage
    return
}

$targetName = Normalize-Target $Target
$repoRoot = Resolve-RepoRoot
. (Join-Path $repoRoot "scripts\env\native_host_guard.ps1")
Assert-SsaWindowsHost -RepoRoot $repoRoot -ExpectedRoot (Get-SsaWindowsRepoRoot)
Assert-SsaWindowsVenv -VenvDir (Join-Path $repoRoot ".venv")
$backendCsv = Join-ReleaseCsv $Backend $DefaultBackend

Write-Host "Release target: $targetName"
Write-Host "Backend: $backendCsv"
Invoke-WindowsRelease $repoRoot $backendCsv

Write-Host "Release concluido."
