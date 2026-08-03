[Diagnostics.CodeAnalysis.SuppressMessageAttribute('PSUseSingularNouns', 'Get-ReleaseTargetNames', Justification = 'Internal helper returns a list of release target names.')]
[Diagnostics.CodeAnalysis.SuppressMessageAttribute('PSUseSingularNouns', 'Get-SelectedBackends', Justification = 'Internal helper returns a list of selected backends.')]
[Diagnostics.CodeAnalysis.SuppressMessageAttribute('PSUseSingularNouns', 'Assert-ExeMetadata', Justification = 'Metadata is the conventional noun for executable version records.')]
[Diagnostics.CodeAnalysis.SuppressMessageAttribute('PSUseSingularNouns', 'Write-BackendReleaseZips', Justification = 'Internal helper writes multiple backend ZIP artifacts.')]
[Diagnostics.CodeAnalysis.SuppressMessageAttribute('PSUseSingularNouns', 'Assert-ZipContents', Justification = 'Internal helper validates ZIP content records.')]
param(
    [string[]] $Backend,
    [switch] $Yes,
    [switch] $SkipBuild,
    [switch] $SkipPackage,
    [switch] $SkipInstaller,
    [switch] $IncludeRuntimeDb,
    [switch] $DryRun
)

Set-StrictMode -Version 3.0
$ErrorActionPreference = "Stop"

$Platform = "windows_amd64"
$DistributionModule = "scripts.create_distribution"
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

    if ($Command -notin @("git", "uv")) {
        throw "Comando de repo nao permitido: $Command"
    }

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

    $staged = @(Invoke-RepoCommand $RepoRoot "git" @("diff", "--cached", "--name-only"))
    $unstaged = @(Invoke-RepoCommand $RepoRoot "git" @("diff", "--ignore-cr-at-eol", "--name-only"))
    $untracked = @(Invoke-RepoCommand $RepoRoot "git" @("ls-files", "--others", "--exclude-standard"))
    $dirty = @($staged + $unstaged + $untracked | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    if ($dirty.Count -gt 0) {
        throw "Workspace sujo. Release Windows requer fonte versionada e limpa.`n$($dirty -join [Environment]::NewLine)"
    }
    return $dirty
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

function Get-ReleaseTargetNames {
    param(
        [Parameter(Mandatory = $true)] [string] $RepoRoot,
        [Parameter(Mandatory = $true)] [string] $Kind
    )

    $targetOutput = Invoke-RepoCommand $RepoRoot "uv" @(
        "run",
        "--python",
        "3.13",
        "python",
        "dev_env\build\release_platform_report.py",
        "release-targets",
        "--platform",
        $Platform,
        "--kind",
        $Kind
    )
    $targets = @($targetOutput -split "," | ForEach-Object { $_.Trim().ToLowerInvariant() } | Where-Object { $_ })
    if ($targets.Count -eq 0) {
        throw "Nenhum target $Kind retornado para $Platform."
    }
    return $targets
}

function Get-SelectedBackends {
    param(
        [string[]] $RequestedBackends,
        [Parameter(Mandatory = $true)] [string[]] $ValidBackends
    )

    $valid = @($ValidBackends)
    if (-not $RequestedBackends -or $RequestedBackends.Count -eq 0) {
        Write-Output "Backends disponiveis: $($valid -join ', '), all"
        $raw = Read-Host "Informe um ou mais backends separados por virgula"
        $RequestedBackends = $raw -split "," | ForEach-Object { $_.Trim().ToLowerInvariant() } | Where-Object { $_ }
    }

    $normalized = @()
    foreach ($item in $RequestedBackends) {
        foreach ($token in ($item -split ",")) {
            $value = $token.Trim().ToLowerInvariant()
            if (-not [string]::IsNullOrWhiteSpace($value)) {
                $normalized += $value
            }
        }
    }

    if ($normalized -contains "all") {
        return $valid
    }

    foreach ($item in $normalized) {
        if ($valid -notcontains $item) {
            throw "Backend invalido: $item"
        }
    }
    return @($normalized | Select-Object -Unique)
}

function Get-BackendScorecard {
    param([Parameter(Mandatory = $true)] [string] $RepoRoot)

    $scorecardFile = Join-Path $RepoRoot "dev_env\build\backend_scorecards.json"
    Assert-ExistingFile $scorecardFile
    $raw = Get-Content $scorecardFile -Raw -Encoding UTF8 | ConvertFrom-Json
    $scorecards = @{}
    foreach ($backend in $raw.PSObject.Properties) {
        $record = [ordered]@{}
        foreach ($field in $backend.Value.PSObject.Properties) {
            $record[$field.Name] = $field.Value
        }
        $scorecards[$backend.Name] = $record
    }
    return $scorecards
}

function Get-BackendConfig {
    param(
        [Parameter(Mandatory = $true)] [string] $RepoRoot,
        [Parameter(Mandatory = $true)] [string] $Version
    )

    return @{
        pyinstaller = [ordered]@{
            build_script = (Join-Path $RepoRoot "dev_env\build\build_pyinstaller.bat")
            package_system = "pyinstaller"
            cli_exe = (Join-Path $RepoRoot "launchers\dist\windows_amd64\SSA_CLI_v$($Version)_windows_amd64\SSA_CLI_v$($Version)_windows_amd64.exe")
            gui_exe = (Join-Path $RepoRoot "launchers\dist\windows_amd64\SSA_GUI_v$($Version)_windows_amd64\SSA_GUI_v$($Version)_windows_amd64.exe")
            build_info = @(
                (Join-Path $RepoRoot "launchers\dist\windows_amd64\SSA_CLI_v$($Version)_windows_amd64\_internal\config\build_info.json"),
                (Join-Path $RepoRoot "launchers\dist\windows_amd64\SSA_GUI_v$($Version)_windows_amd64\_internal\config\build_info.json")
            )
            release_zips = @(
                [ordered]@{
                    source = (Join-Path $RepoRoot "launchers\dist\windows_amd64\SSA_CLI_v$($Version)_windows_amd64")
                    zip = (Join-Path $RepoRoot "builds\packages\windows_amd64\SSA_Consulta_Rapida_v$($Version)_windows_amd64_pyinstaller_cli.zip")
                },
                [ordered]@{
                    source = (Join-Path $RepoRoot "launchers\dist\windows_amd64\SSA_GUI_v$($Version)_windows_amd64")
                    zip = (Join-Path $RepoRoot "builds\packages\windows_amd64\SSA_Consulta_Rapida_v$($Version)_windows_amd64_pyinstaller_gui.zip")
                }
            )
        }
        nuitka = [ordered]@{
            build_script = (Join-Path $RepoRoot "dev_env\build\build_nuitka.bat")
            package_system = "nuitka"
            cli_exe = (Join-Path $RepoRoot "builds\nuitka\windows_amd64\cli_entry.dist\SSA_CLI_v$($Version)_windows_amd64.exe")
            gui_exe = (Join-Path $RepoRoot "builds\nuitka\windows_amd64\gui_entry.dist\SSA_GUI_v$($Version)_windows_amd64.exe")
            build_info = @(
                (Join-Path $RepoRoot "builds\nuitka\windows_amd64\cli_entry.dist\config\build_info.json"),
                (Join-Path $RepoRoot "builds\nuitka\windows_amd64\gui_entry.dist\config\build_info.json")
            )
            release_zips = @(
                [ordered]@{
                    source = (Join-Path $RepoRoot "builds\nuitka\windows_amd64\cli_entry.dist")
                    zip = (Join-Path $RepoRoot "builds\packages\windows_amd64\SSA_Consulta_Rapida_v$($Version)_windows_amd64_nuitka_cli.zip")
                },
                [ordered]@{
                    source = (Join-Path $RepoRoot "builds\nuitka\windows_amd64\gui_entry.dist")
                    zip = (Join-Path $RepoRoot "builds\packages\windows_amd64\SSA_Consulta_Rapida_v$($Version)_windows_amd64_nuitka_gui.zip")
                }
            )
        }
        pyoxidizer = [ordered]@{
            build_script = (Join-Path $RepoRoot "dev_env\build\build_pyoxidizer.bat")
            package_system = "pyoxidizer"
            cli_exe = $null
            gui_exe = (Join-Path $RepoRoot "builds\pyoxidizer\windows_amd64\SSA_Consulta_Rapida.exe")
            build_info = @(
                (Join-Path $RepoRoot "builds\pyoxidizer\windows_amd64\config\build_info.json")
            )
            release_zips = @(
                [ordered]@{
                    source = (Join-Path $RepoRoot "builds\pyoxidizer\windows_amd64")
                    zip = (Join-Path $RepoRoot "builds\packages\windows_amd64\SSA_Consulta_Rapida_v$($Version)_windows_amd64_pyoxidizer.zip")
                }
            )
        }
    }
}

function Get-UserWorkspaceRelativeDirectory {
    return @(
        "data",
        "data\historico_backups",
        "docs_entrada",
        "docs_saida",
        "logs",
        "reports",
        "exportacao"
    )
}

function Get-BackendCleanupPath {
    param(
        [Parameter(Mandatory = $true)] [string] $RepoRoot,
        [Parameter(Mandatory = $true)] [string] $BackendName,
        [Parameter(Mandatory = $true)] [string] $Version
    )

    switch ($BackendName) {
        'pyinstaller' {
            return @(
                (Join-Path $RepoRoot "launchers\dist\windows_amd64"),
                (Join-Path $RepoRoot "builds\pyinstaller\windows_amd64"),
                (Join-Path $RepoRoot "launchers\platforms\windows_amd64\temp")
            )
        }
        'nuitka' {
            $nuitkaRoot = Join-Path $RepoRoot "builds\nuitka\windows_amd64"
            return @(
                (Join-Path $nuitkaRoot "gui_entry.dist"),
                (Join-Path $nuitkaRoot "cli_entry.dist"),
                (Join-Path $nuitkaRoot "gui_entry.build"),
                (Join-Path $nuitkaRoot "cli_entry.build"),
                (Join-Path $nuitkaRoot "SSA_GUI_v$($Version)_windows_amd64.dist"),
                (Join-Path $nuitkaRoot "SSA_CLI_v$($Version)_windows_amd64.dist")
            )
        }
        'pyoxidizer' {
            return @(
                (Join-Path $RepoRoot "builds\pyoxidizer\windows_amd64")
            )
        }
        default {
            throw "Backend sem paths de cleanup: $BackendName"
        }
    }
}

function Invoke-BackendCleanup {
    param(
        [Parameter(Mandatory = $true)] [string] $RepoRoot,
        [Parameter(Mandatory = $true)] [string] $BackendName,
        [Parameter(Mandatory = $true)] [string] $Version
    )

    $removed = @()
    $paths = Get-BackendCleanupPath -RepoRoot $RepoRoot -BackendName $BackendName -Version $Version
    foreach ($path in $paths) {
        if (Test-Path -LiteralPath $path) {
            Remove-Item -LiteralPath $path -Recurse -Force
            $removed += $path
        }
    }
    return $removed
}

function Get-RuntimeBundleRoot {
    param(
        [Parameter(Mandatory = $true)] [hashtable] $Config
    )

    $roots = @()
    foreach ($item in $Config.release_zips) {
        if ($item.source -and ($roots -notcontains $item.source)) {
            $roots += $item.source
        }
    }
    return $roots
}

function Initialize-UserWorkspaceDirectory {
    param(
        [Parameter(Mandatory = $true)] [string[]] $RuntimeRoot
    )

    $created = @()
    $relativeDirs = Get-UserWorkspaceRelativeDirectory
    foreach ($root in $RuntimeRoot) {
        if (-not (Test-Path -LiteralPath $root -PathType Container)) {
            continue
        }
        foreach ($rel in $relativeDirs) {
            $dir = Join-Path $root $rel
            if (-not (Test-Path -LiteralPath $dir)) {
                New-Item -ItemType Directory -Path $dir -Force | Out-Null
                $created += $dir
            }
            $gitkeep = Join-Path $dir ".gitkeep"
            if (-not (Test-Path -LiteralPath $gitkeep -PathType Leaf)) {
                New-Item -ItemType File -Path $gitkeep -Force | Out-Null
            }
        }
    }
    return $created
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

    $smokeExe = $Config.cli_exe
    if ([string]::IsNullOrWhiteSpace($smokeExe)) {
        $smokeExe = $Config.gui_exe
    }
    if ([string]::IsNullOrWhiteSpace($smokeExe)) {
        throw "Smoke importacao sem executavel para ${BackendName}."
    }

    $smokeJsonPath = Join-Path ([System.IO.Path]::GetTempPath()) ("ssa_release_smoke_" + [guid]::NewGuid().ToString("N") + ".json")
    $smokeErrPath = Join-Path ([System.IO.Path]::GetTempPath()) ("ssa_release_smoke_" + [guid]::NewGuid().ToString("N") + ".err")
    try {
        $smokeScript = (Resolve-Path (Join-Path $PSScriptRoot "..\..\scripts\smoke_cli.py")).Path
        $smokeExePath = (Resolve-Path $smokeExe).Path
        $smokeProcess = Start-Process -FilePath "uv" -ArgumentList @(
            "run",
            "--python",
            "3.13",
            "python",
            $smokeScript,
            "--executable",
            $smokeExePath,
            "--json"
        ) -NoNewWindow -Wait -PassThru -RedirectStandardOutput $smokeJsonPath -RedirectStandardError $smokeErrPath
        $stderrText = ""
        if (Test-Path $smokeErrPath) {
            $stderrText = ([string]::Join([Environment]::NewLine, @(Get-Content -LiteralPath $smokeErrPath -ErrorAction SilentlyContinue))).Trim()
        }
        $stdoutText = ""
        if (Test-Path $smokeJsonPath) {
            $stdoutText = ([string]::Join([Environment]::NewLine, @(Get-Content -LiteralPath $smokeJsonPath -ErrorAction SilentlyContinue))).Trim()
        }
        if ($smokeProcess.ExitCode -ne 0) {
            throw "Smoke importacao falhou para ${BackendName}. stdout=${stdoutText} stderr=${stderrText}"
        }
        try {
            $payload = $stdoutText | ConvertFrom-Json -ErrorAction Stop
        } catch {
            throw "Smoke importacao gerou JSON invalido para ${BackendName}. stdout=${stdoutText} stderr=${stderrText} erro=$($_.Exception.Message)"
        }
        if ($null -eq $payload -or $null -eq $payload.summary) {
            throw "Smoke importacao sem summary JSON para ${BackendName}. stdout=${stdoutText} stderr=${stderrText}"
        }
        if (-not $payload.summary.ok -or [int] $payload.summary.imported_rows -lt 1) {
            throw "Smoke importacao nao validou SQLite para ${BackendName}. stdout=${stdoutText} stderr=${stderrText}"
        }
        $smokeOutput = [string] $payload.summary.output
        $smokeImportedRows = [int] $payload.summary.imported_rows
    } finally {
        Remove-Item -LiteralPath $smokeJsonPath -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $smokeErrPath -Force -ErrorAction SilentlyContinue
    }
    return [ordered]@{
        verification_type = "functional_import_check"
        command = "$smokeExePath --force-rescan"
        exit_code = 0
        imported_rows = $smokeImportedRows
        executable = $smokeExePath
        output = $smokeOutput
    }
}

function Write-BackendReleaseZips {
    param(
        [Parameter(Mandatory = $true)] [array] $ReleaseZips
    )

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    foreach ($item in $ReleaseZips) {
        $outDir = Split-Path -Parent $item.zip
        New-Item -ItemType Directory -Force $outDir | Out-Null
        Assert-ExistingDirectory $item.source
        if (Test-Path -LiteralPath $item.zip -PathType Leaf) {
            Remove-Item -LiteralPath $item.zip -Force
        }
        [System.IO.Compression.ZipFile]::CreateFromDirectory(
            (Resolve-Path $item.source).Path,
            $item.zip,
            [System.IO.Compression.CompressionLevel]::Optimal,
            $false
        )
    }
}

function Assert-ZipContents {
    param(
        [Parameter(Mandatory = $true)] [array] $ZipPaths,
        [string] $ExpectedRuntimeDbHash
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
            $sensitiveEntries = @($archive.Entries | Where-Object {
                [System.IO.Path]::GetExtension($_.FullName).ToLowerInvariant() -in @(".db", ".ods", ".xls", ".xlsm", ".xlsx")
            })
            $runtimeEntries = @($sensitiveEntries | Where-Object {
                $normalized = $_.FullName.Replace("\", "/")
                $normalized.EndsWith("/data/ssas.db") -and -not $normalized.Contains("/_internal/")
            })
            $runtimeHash = $null
            if (-not $hasBuildInfo) {
                throw "ZIP sem build_info.json: $path"
            }
            if (-not $hasGuide) {
                throw "ZIP sem ${MandatoryGuideName}: $path"
            }
            if (-not $hasExe) {
                throw "ZIP sem exe: $path"
            }
            if ([string]::IsNullOrWhiteSpace($ExpectedRuntimeDbHash)) {
                if ($sensitiveEntries.Count -gt 0) {
                    throw "ZIP contem DB/XLS/XLSX sem autorizacao: $path"
                }
            } else {
                if ($sensitiveEntries.Count -ne 1 -or $runtimeEntries.Count -ne 1) {
                    throw "ZIP deve conter somente data/ssas.db externo: $path"
                }
                $runtimeStream = $runtimeEntries[0].Open()
                $runtimeSha256 = $null
                try {
                    $runtimeSha256 = [System.Security.Cryptography.SHA256]::Create()
                    $runtimeHashBytes = $runtimeSha256.ComputeHash($runtimeStream)
                    $runtimeHash = ([System.BitConverter]::ToString($runtimeHashBytes) -replace "-", "").ToUpperInvariant()
                }
                finally {
                    if ($runtimeSha256) {
                        $runtimeSha256.Dispose()
                    }
                    $runtimeStream.Dispose()
                }
                if ($runtimeHash -ne $ExpectedRuntimeDbHash) {
                    throw "Hash do banco de runtime diverge no ZIP ${path}: $runtimeHash != $ExpectedRuntimeDbHash"
                }
            }
            $records += [ordered]@{
                path = $path
                entry_count = $entries.Count
                has_build_info = $hasBuildInfo
                has_guide = $hasGuide
                has_exe = $hasExe
                runtime_db_sha256 = $runtimeHash
            }
        }
        finally {
            $archive.Dispose()
        }
    }
    return $records
}

function Assert-SourceProtection {
    param(
        [Parameter(Mandatory = $true)] [string] $RepoRoot,
        [Parameter(Mandatory = $true)] [string[]] $ArtifactPaths
    )

    $records = @()
    foreach ($path in $ArtifactPaths) {
        if (Test-Path -LiteralPath $path -PathType Leaf) {
            Assert-ExistingFile $path
        } elseif (Test-Path -LiteralPath $path -PathType Container) {
            Assert-ExistingDirectory $path
        } else {
            throw "Artefato para protecao de fonte ausente: $path"
        }
        Invoke-CheckedProcess $RepoRoot "uv" @(
            "run",
            "--python",
            "3.13",
            "dev_env\build\release_platform_report.py",
            "source-protection",
            "--repo-root",
            $RepoRoot,
            "--artifact",
            $path
        )
        $records += [ordered]@{
            path = $path
            protected_python_source = $true
        }
    }
    return $records
}

function Get-ArtifactHash {
    param([Parameter(Mandatory = $true)] [string[]] $Paths)

    $records = @()
    $hashCommand = Get-Command -Name "Get-FileHash" -ErrorAction SilentlyContinue
    foreach ($path in $Paths) {
        Assert-ExistingFile $path
        if ($hashCommand) {
            $hash = & $hashCommand -Algorithm SHA256 -LiteralPath $path
            $hashPath = $hash.Path
            $hashValue = $hash.Hash
        }
        else {
            $stream = [System.IO.File]::OpenRead($path)
            $sha256 = $null
            try {
                $sha256 = [System.Security.Cryptography.SHA256]::Create()
                $hashBytes = $sha256.ComputeHash($stream)
                $hashValue = ([System.BitConverter]::ToString($hashBytes) -replace "-", "").ToUpperInvariant()
            }
            finally {
                if ($sha256) {
                    $sha256.Dispose()
                }
                $stream.Dispose()
            }
            $hashPath = (Resolve-Path -LiteralPath $path).Path
        }
        $records += [ordered]@{
            path = $hashPath
            sha256 = $hashValue
            length = (Get-Item -LiteralPath $path).Length
        }
    }
    return $records
}

function Assert-RuntimeDatabase {
    param(
        [Parameter(Mandatory = $true)] [string] $RepoRoot,
        [Parameter(Mandatory = $true)] [string[]] $RuntimeRoot
    )

    $sourcePath = Join-Path $RepoRoot "data\ssas.db"
    $sourceHash = @(Get-ArtifactHash @($sourcePath))[0]
    $records = @()
    foreach ($root in $RuntimeRoot) {
        Assert-ExistingDirectory $root
        $runtimePath = Join-Path $root "data\ssas.db"
        $runtimeHash = @(Get-ArtifactHash @($runtimePath))[0]
        if ($runtimeHash['sha256'] -ne $sourceHash['sha256']) {
            throw "Hash do banco de runtime diverge em ${runtimePath}: $($runtimeHash['sha256']) != $($sourceHash['sha256'])"
        }
        $sensitiveFiles = @(Get-ChildItem -LiteralPath $root -Recurse -File | Where-Object {
            $_.Extension.ToLowerInvariant() -in @(".db", ".ods", ".xls", ".xlsm", ".xlsx")
        })
        $unexpected = @($sensitiveFiles | Where-Object {
            $_.FullName -ne $runtimeHash.path
        })
        if ($unexpected.Count -gt 0) {
            throw "Bundle contem DB/XLS/XLSX nao autorizado: $($unexpected.FullName -join ', ')"
        }
        $records += [ordered]@{
            source = $sourceHash.path
            path = $runtimeHash.path
            sha256 = $runtimeHash['sha256']
            length = $runtimeHash.length
        }
    }
    return $records
}

function Invoke-DistributionPackage {
    param(
        [Parameter(Mandatory = $true)] [string] $RepoRoot,
        [Parameter(Mandatory = $true)] [string] $BackendName,
        [Parameter(Mandatory = $true)] [bool] $SkipInstallerFlag,
        [Parameter(Mandatory = $true)] [bool] $IncludeRuntimeDbFlag
    )

    $distributionArgs = @("run", "--python", "3.13", "python", "-m", $DistributionModule, "--build-system", $BackendName)
    if ($SkipInstallerFlag) {
        $distributionArgs += "--skip-installer"
    }
    if ($IncludeRuntimeDbFlag) {
        $distributionArgs += "--include-runtime-db"
    }
    Invoke-CheckedProcess $RepoRoot "uv" $distributionArgs
}

function Write-ReleaseReport {
    param(
        [Parameter(Mandatory = $true)] [string] $RepoRoot,
        [Parameter(Mandatory = $true)] [hashtable] $Report
    )

    $reportDir = Join-Path $RepoRoot "builds\reports"
    New-Item -ItemType Directory -Force $reportDir | Out-Null
    $reportPath = Join-Path $reportDir "release_report_windows_amd64.json"
    $reportJson = $Report | ConvertTo-Json -Depth 12
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($reportPath, $reportJson + [Environment]::NewLine, $utf8NoBom)
    return $reportPath
}

Assert-WindowsHost
Assert-PowerShellHost
Assert-Tool "git" "instale Git para Windows"
Assert-Tool "uv" "instale uv"

$repoRoot = Resolve-RepoRoot
$validBackends = Get-ReleaseTargetNames $repoRoot "backends"
$selectedBackends = Get-SelectedBackends $Backend $validBackends
if ((-not $DryRun) -and (-not $SkipInstaller)) {
    Assert-Tool "iscc" "instale Inno Setup ou use -SkipInstaller"
}
if ((-not $DryRun) -and (-not $SkipBuild) -and ($selectedBackends -contains "pyoxidizer")) {
    Assert-Tool "rcedit.exe" "scoop install rcedit"
    $pyoxidizerPackage = if ($env:SSA_PYOXIDIZER_UV_PACKAGE) { $env:SSA_PYOXIDIZER_UV_PACKAGE } else { "pyoxidizer==0.24.0" }
    $pyoxidizerCheck = & uv @(
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
        throw "PyOxidizer indisponivel via uv tool: $pyoxidizerPackage. Saida: $($pyoxidizerCheck -join [Environment]::NewLine)"
    }
}
$version = Get-AppVersion $repoRoot
$windowsVersion = Get-WindowsVersionText $version
$gitHead = Get-GitHead $repoRoot
$dirtyEntries = Assert-CleanReleaseWorkspace $repoRoot
$scorecard = Get-BackendScorecard $repoRoot

if ($DryRun) {
    Write-Output "Dry-run Windows concluido sem build/pacote."
    Write-Output "Repo: $repoRoot"
    Write-Output "HEAD: $($gitHead.commit)"
    Write-Output "Versao: $version"
    Write-Output "Backends: $($selectedBackends -join ', ')"
    foreach ($backendName in $selectedBackends) {
        $backendScore = $scorecard[$backendName]
        Write-Output "Scorecard ${backendName}: seguranca=$($backendScore.security_score); python=$($backendScore.source_protection_score); pastas=$($backendScore.easy_user_dirs_score); tamanho=$($backendScore.package_size_score); nota=$($backendScore.note)"
    }
    return
}

if (-not $Yes) {
    Write-Output "Repo: $repoRoot"
    Write-Output "HEAD: $($gitHead.commit)"
    Write-Output "Backends: $($selectedBackends -join ', ')"
    $confirm = Read-Host "Continuar? [s/N]"
    if ($confirm.ToLowerInvariant() -ne "s") {
        throw "Operacao cancelada pelo usuario."
    }
}

$configs = Get-BackendConfig $repoRoot $version
$results = @()

foreach ($backendName in $selectedBackends) {
    $config = $configs[$backendName]
    $cleanupRemoved = @()
    $userDirsCreated = @()
    $runtimeProtectionRecords = @()
    $runtimeDatabaseRecords = @()
    if (-not $SkipBuild) {
        $cleanupRemoved = @(Invoke-BackendCleanup -RepoRoot $repoRoot -BackendName $backendName -Version $version)
        $buildArgs = @("--silent")
        if ($IncludeRuntimeDb -and $backendName -eq "pyinstaller") {
            $buildArgs += "--with-runtime-db"
        }
        Invoke-CheckedProcess $repoRoot $config.build_script $buildArgs
    }

    $buildInfoRecords = Assert-BuildInfo $config.build_info $gitHead.commit $Platform $config.package_system
    $exePaths = @($config.cli_exe, $config.gui_exe) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    $metadataRecords = Assert-ExeMetadata $exePaths $windowsVersion
    $smokeRecord = Invoke-Smoke $backendName $config
    $runtimeRoots = @(Get-RuntimeBundleRoot -Config $config)
    if ($IncludeRuntimeDb -and $backendName -eq "pyinstaller") {
        $runtimeDatabaseRecords = @(Assert-RuntimeDatabase -RepoRoot $repoRoot -RuntimeRoot $runtimeRoots)
    }
    $userDirsCreated = @(Initialize-UserWorkspaceDirectory -RuntimeRoot $runtimeRoots)
    $runtimeProtectionRecords = @(Assert-SourceProtection $repoRoot $runtimeRoots)
    $zipRecords = @()
    $zipProtectionRecords = @()
    $hashRecords = @()
    if (-not $SkipPackage) {
        Write-BackendReleaseZips $config.release_zips
        $includeBackendRuntimeDb = [bool]($IncludeRuntimeDb -and $backendName -eq "pyinstaller")
        Invoke-DistributionPackage $repoRoot $config.package_system ([bool] $SkipInstaller) $includeBackendRuntimeDb
        $zipPaths = @($config.release_zips | ForEach-Object { $_.zip })
        $runtimeDbHash = if ($runtimeDatabaseRecords.Count -gt 0) { $runtimeDatabaseRecords[0]['sha256'] } else { $null }
        $zipRecords = @(Assert-ZipContents $zipPaths $runtimeDbHash)
        $zipProtectionRecords = @(Assert-SourceProtection $repoRoot $zipPaths)
        $hashRecords = @(Get-ArtifactHash $zipPaths)
    }

    $results += [ordered]@{
        backend = $backendName
        scorecard = $scorecard[$backendName]
        cleanup_removed = $cleanupRemoved
        user_dirs_created = $userDirsCreated
        build_info = $buildInfoRecords
        exe_metadata = $metadataRecords
        smoke = $smokeRecord
        runtime_source_protection = $runtimeProtectionRecords
        runtime_database = $runtimeDatabaseRecords
        zip_validation = $zipRecords
        zip_source_protection = $zipProtectionRecords
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
Write-Output "Release Windows concluido. Report: $reportPath"
