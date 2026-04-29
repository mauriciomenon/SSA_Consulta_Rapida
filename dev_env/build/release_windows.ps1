param(
    [ValidateSet("pyinstaller", "nuitka", "pyoxidizer", "all")]
    [string[]] $Backend,
    [switch] $Yes,
    [switch] $SkipBuild,
    [switch] $SkipPackage,
    [switch] $SkipInstaller
)

Set-StrictMode -Version 3.0
$ErrorActionPreference = "Stop"

$Platform = "windows_amd64"
$DistributionScript = "scripts\create_distribution.py"
$MandatoryGuideName = "GUIA_MIGRACAO_NOVA_INSTALACAO.md"

function Assert-WindowsHost {
    if ([System.Environment]::OSVersion.Platform -ne [System.PlatformID]::Win32NT) {
        throw "release_windows.ps1 deve rodar somente em Windows PowerShell."
    }
}

function Assert-PowerShellHost {
    if ($PSVersionTable.PSVersion.Major -lt 5) {
        throw "PowerShell 5 ou superior e requerido."
    }
}

function Invoke-RepoCommand {
    param(
        [Parameter(Mandatory = $true)] [string] $RepoRoot,
        [Parameter(Mandatory = $true)] [string] $Command,
        [string[]] $Arguments = @()
    )

    Push-Location $RepoRoot
    try {
        $output = & $Command @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "Comando falhou: $Command $($Arguments -join ' ')"
        }
        return $output
    }
    finally {
        Pop-Location
    }
}

function Resolve-RepoRoot {
    $root = (git rev-parse --show-toplevel).Trim()
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($root)) {
        throw "Nao foi possivel localizar a raiz git."
    }
    return (Resolve-Path $root).Path
}

function Assert-Tool {
    param(
        [Parameter(Mandatory = $true)] [string] $Name,
        [Parameter(Mandatory = $true)] [string] $InstallHint
    )

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Ferramenta obrigatoria ausente: $Name. Instale/verifique: $InstallHint"
    }
}

function Get-GitHead {
    param([Parameter(Mandatory = $true)] [string] $RepoRoot)

    $commit = (Invoke-RepoCommand $RepoRoot "git" @("rev-parse", "HEAD")).Trim()
    $commitDate = (Invoke-RepoCommand $RepoRoot "git" @("log", "-1", "--format=%cI")).Trim()
    $title = (Invoke-RepoCommand $RepoRoot "git" @("log", "-1", "--format=%s")).Trim()
    return [ordered]@{
        commit = $commit
        short = $commit.Substring(0, 7)
        commit_datetime = $commitDate
        title = $title
    }
}

function Assert-CleanReleaseWorkspace {
    param(
        [Parameter(Mandatory = $true)] [string] $RepoRoot
    )

    $status = @(Invoke-RepoCommand $RepoRoot "git" @("status", "--porcelain=v1"))
    if ($status.Count -gt 0) {
        throw "Workspace sujo. Release Windows requer fonte versionada e limpa.`n$($status -join [Environment]::NewLine)"
    }
    return $status
}

function Get-AppVersion {
    param([Parameter(Mandatory = $true)] [string] $RepoRoot)

    $versionFile = Join-Path $RepoRoot "config\version.json"
    $versionJson = Get-Content $versionFile -Raw -Encoding UTF8 | ConvertFrom-Json
    return [string] $versionJson.version_short
}

function Get-WindowsVersionText {
    param([Parameter(Mandatory = $true)] [string] $Version)

    $parts = [regex]::Matches($Version, "\d+") | ForEach-Object { [int] $_.Value } | Select-Object -First 4
    $list = @($parts)
    while ($list.Count -lt 4) {
        $list += 0
    }
    return ($list[0..3] -join ".")
}

function Get-SelectedBackends {
    param([string[]] $RequestedBackends)

    $valid = @("pyinstaller", "nuitka", "pyoxidizer")
    if (-not $RequestedBackends -or $RequestedBackends.Count -eq 0) {
        Write-Host "Backends disponiveis: pyinstaller, nuitka, pyoxidizer, all"
        $raw = Read-Host "Informe um ou mais backends separados por virgula"
        $RequestedBackends = $raw -split "," | ForEach-Object { $_.Trim().ToLowerInvariant() } | Where-Object { $_ }
    }

    if ($RequestedBackends -contains "all") {
        return $valid
    }

    foreach ($item in $RequestedBackends) {
        if ($valid -notcontains $item) {
            throw "Backend invalido: $item"
        }
    }
    return @($RequestedBackends | Select-Object -Unique)
}

function Get-BackendScorecard {
    return [ordered]@{
        pyinstaller = [ordered]@{
            security_score = 2
            python_source_exposure_score = 2
            easy_user_dirs_score = 5
            package_size_score = 4
            note = "Alta compatibilidade; menor protecao contra inspecao do Python empacotado."
        }
        nuitka = [ordered]@{
            security_score = 4
            python_source_exposure_score = 4
            easy_user_dirs_score = 4
            package_size_score = 3
            note = "Melhor protecao do codigo Python; build mais lento e dependente de toolchain."
        }
        pyoxidizer = [ordered]@{
            security_score = 3
            python_source_exposure_score = 3
            easy_user_dirs_score = 3
            package_size_score = 2
            note = "Empacotamento forte, mas o layout atual ainda expoe varias pastas Python no output."
        }
    }
}

function Get-BackendConfig {
    param(
        [Parameter(Mandatory = $true)] [string] $RepoRoot,
        [Parameter(Mandatory = $true)] [string] $Version
    )

    return @{
        pyinstaller = [ordered]@{
            build_script = Join-Path $RepoRoot "dev_env\build\build_pyinstaller.bat"
            package_system = "pyinstaller"
            cli_exe = Join-Path $RepoRoot "launchers\dist\windows_amd64\SSA_CLI_v$($Version)_windows_amd64\SSA_CLI_v$($Version)_windows_amd64.exe"
            gui_exe = Join-Path $RepoRoot "launchers\dist\windows_amd64\SSA_GUI_v$($Version)_windows_amd64\SSA_GUI_v$($Version)_windows_amd64.exe"
            build_info = @(
                Join-Path $RepoRoot "launchers\dist\windows_amd64\SSA_CLI_v$($Version)_windows_amd64\_internal\config\build_info.json",
                Join-Path $RepoRoot "launchers\dist\windows_amd64\SSA_GUI_v$($Version)_windows_amd64\_internal\config\build_info.json"
            )
            release_zips = @(
                [ordered]@{
                    source = Join-Path $RepoRoot "launchers\dist\windows_amd64\SSA_CLI_v$($Version)_windows_amd64"
                    zip = Join-Path $RepoRoot "builds\packages\windows_amd64\SSA_Consulta_Rapida_v$($Version)_windows_amd64_pyinstaller_cli.zip"
                },
                [ordered]@{
                    source = Join-Path $RepoRoot "launchers\dist\windows_amd64\SSA_GUI_v$($Version)_windows_amd64"
                    zip = Join-Path $RepoRoot "builds\packages\windows_amd64\SSA_Consulta_Rapida_v$($Version)_windows_amd64_pyinstaller_gui.zip"
                }
            )
        }
        nuitka = [ordered]@{
            build_script = Join-Path $RepoRoot "dev_env\build\build_nuitka.bat"
            package_system = "nuitka"
            cli_exe = Join-Path $RepoRoot "builds\nuitka\windows_amd64\cli_entry.dist\SSA_CLI_v$($Version)_windows_amd64.exe"
            gui_exe = Join-Path $RepoRoot "builds\nuitka\windows_amd64\gui_entry.dist\SSA_GUI_v$($Version)_windows_amd64.exe"
            build_info = @(
                Join-Path $RepoRoot "builds\nuitka\windows_amd64\cli_entry.dist\config\build_info.json",
                Join-Path $RepoRoot "builds\nuitka\windows_amd64\gui_entry.dist\config\build_info.json"
            )
            release_zips = @(
                [ordered]@{
                    source = Join-Path $RepoRoot "builds\nuitka\windows_amd64\cli_entry.dist"
                    zip = Join-Path $RepoRoot "builds\packages\windows_amd64\SSA_Consulta_Rapida_v$($Version)_windows_amd64_nuitka_cli.zip"
                },
                [ordered]@{
                    source = Join-Path $RepoRoot "builds\nuitka\windows_amd64\gui_entry.dist"
                    zip = Join-Path $RepoRoot "builds\packages\windows_amd64\SSA_Consulta_Rapida_v$($Version)_windows_amd64_nuitka_gui.zip"
                }
            )
        }
        pyoxidizer = [ordered]@{
            build_script = Join-Path $RepoRoot "dev_env\build\build_pyoxidizer.bat"
            package_system = "pyoxidizer"
            cli_exe = $null
            gui_exe = Join-Path $RepoRoot "builds\pyoxidizer\windows_amd64\SSA_Consulta_Rapida.exe"
            build_info = @(
                Join-Path $RepoRoot "builds\pyoxidizer\windows_amd64\config\build_info.json"
            )
            release_zips = @(
                [ordered]@{
                    source = Join-Path $RepoRoot "builds\pyoxidizer\windows_amd64"
                    zip = Join-Path $RepoRoot "builds\packages\windows_amd64\SSA_Consulta_Rapida_v$($Version)_windows_amd64_pyoxidizer.zip"
                }
            )
        }
    }
}

function Invoke-CheckedProcess {
    param(
        [Parameter(Mandatory = $true)] [string] $RepoRoot,
        [Parameter(Mandatory = $true)] [string] $CommandPath,
        [string[]] $Arguments = @()
    )

    Push-Location $RepoRoot
    try {
        & $CommandPath @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "Comando falhou: $CommandPath $($Arguments -join ' ')"
        }
    }
    finally {
        Pop-Location
    }
}

function Assert-ExistingFile {
    param([Parameter(Mandatory = $true)] [string] $Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Arquivo obrigatorio ausente: $Path"
    }
}

function Assert-ExistingDirectory {
    param([Parameter(Mandatory = $true)] [string] $Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
        throw "Diretorio obrigatorio ausente: $Path"
    }
}

function Assert-BuildInfo {
    param(
        [Parameter(Mandatory = $true)] [string[]] $BuildInfoPaths,
        [Parameter(Mandatory = $true)] [string] $ExpectedCommit,
        [Parameter(Mandatory = $true)] [string] $ExpectedPlatform,
        [Parameter(Mandatory = $true)] [string] $ExpectedSystem
    )

    $records = @()
    foreach ($path in $BuildInfoPaths) {
        Assert-ExistingFile $path
        $info = Get-Content $path -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($info.git_commit -ne $ExpectedCommit) {
            throw "build_info stale em ${path}: $($info.git_commit) != $ExpectedCommit"
        }
        if ($info.platform -ne $ExpectedPlatform) {
            throw "build_info platform invalido em ${path}: $($info.platform)"
        }
        if ($info.build_system -ne $ExpectedSystem) {
            throw "build_info build_system invalido em ${path}: $($info.build_system)"
        }
        $records += $info
    }
    return $records
}

function Assert-ExeMetadata {
    param(
        [Parameter(Mandatory = $true)] [string[]] $ExePaths,
        [Parameter(Mandatory = $true)] [string] $ExpectedVersion
    )

    $records = @()
    foreach ($path in $ExePaths | Where-Object { $_ }) {
        Assert-ExistingFile $path
        $info = [System.Diagnostics.FileVersionInfo]::GetVersionInfo((Resolve-Path $path).Path)
        if ($info.FileVersion -ne $ExpectedVersion) {
            throw "FileVersion invalido em ${path}: $($info.FileVersion) != $ExpectedVersion"
        }
        if ($info.ProductVersion -ne $ExpectedVersion) {
            throw "ProductVersion invalido em ${path}: $($info.ProductVersion) != $ExpectedVersion"
        }
        if ([string]::IsNullOrWhiteSpace($info.ProductName)) {
            throw "ProductName vazio em ${path}"
        }
        $records += [ordered]@{
            path = $path
            file_version = $info.FileVersion
            product_version = $info.ProductVersion
            product_name = $info.ProductName
            file_description = $info.FileDescription
            original_filename = $info.OriginalFilename
        }
    }
    return $records
}

function Invoke-Smoke {
    param(
        [Parameter(Mandatory = $true)] [string] $BackendName,
        [Parameter(Mandatory = $true)] [hashtable] $Config
    )

    if ($BackendName -eq "pyoxidizer") {
        $versionOutput = (& $Config.gui_exe --version 2>&1)
        if ($LASTEXITCODE -ne 0) {
            throw "Smoke PyOxidizer --version falhou."
        }
        $versionText = ($versionOutput | Out-String).Trim()
        $verificationType = "version_check_stdout"
        $commandText = "--version"
        if ([string]::IsNullOrWhiteSpace($versionText)) {
            $versionInfo = [System.Diagnostics.FileVersionInfo]::GetVersionInfo((Resolve-Path $Config.gui_exe).Path)
            $versionText = [string] $versionInfo.ProductVersion
            $verificationType = "version_check_metadata"
            $commandText = "--version + FileVersionInfo"
        }
        if ([string]::IsNullOrWhiteSpace($versionText)) {
            throw "Smoke PyOxidizer nao conseguiu confirmar versao por stdout nem FileVersionInfo."
        }
        return [ordered]@{
            verification_type = $verificationType
            command = $commandText
            exit_code = 0
            output = $versionText
        }
    }

    $inputText = "q`n"
    $inputText | & $Config.cli_exe --skip-import | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Smoke CLI falhou para ${BackendName}."
    }
    return [ordered]@{
        verification_type = "functional_cli_check"
        command = "CLI --skip-import"
        exit_code = 0
        output = ""
    }
}

function Write-BackendReleaseZips {
    param(
        [Parameter(Mandatory = $true)] [array] $ReleaseZips
    )

    foreach ($item in $ReleaseZips) {
        $outDir = Split-Path -Parent $item.zip
        New-Item -ItemType Directory -Force $outDir | Out-Null
        Assert-ExistingDirectory $item.source
        Compress-Archive -Force -Path $item.source -DestinationPath $item.zip
    }
}

function Assert-ZipContents {
    param(
        [Parameter(Mandatory = $true)] [array] $ZipPaths
    )

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $records = @()
    foreach ($path in $ZipPaths) {
        Assert-ExistingFile $path
        $archive = [System.IO.Compression.ZipFile]::OpenRead((Resolve-Path $path).Path)
        try {
            $entries = @($archive.Entries | ForEach-Object { $_.FullName })
            $hasBuildInfo = [bool]($entries | Where-Object { $_ -like "*config/build_info.json" -or $_ -like "*config\build_info.json" })
            $hasGuide = [bool]($entries | Where-Object { $_ -like "*$MandatoryGuideName" })
            $hasExe = [bool]($entries | Where-Object { $_ -like "*.exe" })
            if (-not $hasBuildInfo) {
                throw "ZIP sem build_info.json: $path"
            }
            if (-not $hasGuide) {
                throw "ZIP sem ${MandatoryGuideName}: $path"
            }
            if (-not $hasExe) {
                throw "ZIP sem exe: $path"
            }
            $records += [ordered]@{
                path = $path
                entry_count = $entries.Count
                has_build_info = $hasBuildInfo
                has_guide = $hasGuide
                has_exe = $hasExe
            }
        }
        finally {
            $archive.Dispose()
        }
    }
    return $records
}

function Get-ArtifactHash {
    param([Parameter(Mandatory = $true)] [string[]] $Paths)

    $records = @()
    foreach ($path in $Paths) {
        Assert-ExistingFile $path
        $hash = Get-FileHash -Algorithm SHA256 -LiteralPath $path
        $records += [ordered]@{
            path = $hash.Path
            sha256 = $hash.Hash
            length = (Get-Item -LiteralPath $path).Length
        }
    }
    return $records
}

function Invoke-DistributionPackage {
    param(
        [Parameter(Mandatory = $true)] [string] $RepoRoot,
        [Parameter(Mandatory = $true)] [string] $BackendName,
        [Parameter(Mandatory = $true)] [bool] $SkipInstallerFlag
    )

    $args = @("run", "--python", "3.13", $DistributionScript, "--build-system", $BackendName)
    if ($SkipInstallerFlag) {
        $args += "--skip-installer"
    }
    Invoke-CheckedProcess $RepoRoot "uv" $args
}

function Write-ReleaseReport {
    param(
        [Parameter(Mandatory = $true)] [string] $RepoRoot,
        [Parameter(Mandatory = $true)] [hashtable] $Report
    )

    $reportDir = Join-Path $RepoRoot "builds\reports"
    New-Item -ItemType Directory -Force $reportDir | Out-Null
    $reportPath = Join-Path $reportDir "release_report_windows_amd64.json"
    $Report | ConvertTo-Json -Depth 12 | Set-Content -Path $reportPath -Encoding UTF8
    return $reportPath
}

Assert-WindowsHost
Assert-PowerShellHost
$repoRoot = Resolve-RepoRoot
$selectedBackends = Get-SelectedBackends $Backend
$version = Get-AppVersion $repoRoot
$windowsVersion = Get-WindowsVersionText $version
$gitHead = Get-GitHead $repoRoot
$dirtyEntries = Assert-CleanReleaseWorkspace $repoRoot

Assert-Tool "git" "instale Git para Windows"
Assert-Tool "uv" "instale uv"
Assert-Tool "rcedit.exe" "scoop install rcedit"
if (-not $SkipInstaller) {
    Assert-Tool "iscc" "instale Inno Setup ou use -SkipInstaller"
}

if (-not $Yes) {
    Write-Host "Repo: $repoRoot"
    Write-Host "HEAD: $($gitHead.commit)"
    Write-Host "Backends: $($selectedBackends -join ', ')"
    $confirm = Read-Host "Continuar? [s/N]"
    if ($confirm.ToLowerInvariant() -ne "s") {
        throw "Operacao cancelada pelo usuario."
    }
}

$configs = Get-BackendConfig $repoRoot $version
$scorecard = Get-BackendScorecard
$results = @()

foreach ($backendName in $selectedBackends) {
    $config = $configs[$backendName]
    if (-not $SkipBuild) {
        Invoke-CheckedProcess $repoRoot $config.build_script @("--silent")
    }

    $buildInfoRecords = Assert-BuildInfo $config.build_info $gitHead.commit $Platform $config.package_system
    $metadataRecords = Assert-ExeMetadata @($config.cli_exe, $config.gui_exe) $windowsVersion
    $smokeRecord = Invoke-Smoke $backendName $config

    if (-not $SkipPackage) {
        Write-BackendReleaseZips $config.release_zips
        Invoke-DistributionPackage $repoRoot $config.package_system ([bool] $SkipInstaller)
    }

    $zipPaths = @($config.release_zips | ForEach-Object { $_.zip })
    $zipRecords = Assert-ZipContents $zipPaths
    $hashRecords = Get-ArtifactHash $zipPaths

    $results += [ordered]@{
        backend = $backendName
        scorecard = $scorecard[$backendName]
        build_info = $buildInfoRecords
        exe_metadata = $metadataRecords
        smoke = $smokeRecord
        zip_validation = $zipRecords
        hashes = $hashRecords
    }
}

$report = [ordered]@{
    schema_version = 1
    generated_at = (Get-Date).ToString("o")
    platform = $Platform
    repo_root = $repoRoot
    powershell = [ordered]@{
        edition = $PSVersionTable.PSEdition
        version = $PSVersionTable.PSVersion.ToString()
    }
    os = [System.Environment]::OSVersion.VersionString
    git = $gitHead
    dirty_entries = $dirtyEntries
    selected_backends = $selectedBackends
    backend_scorecard = $scorecard
    results = $results
}

$reportPath = Write-ReleaseReport $repoRoot $report
Write-Host "Release Windows concluido. Report: $reportPath"
