[CmdletBinding(PositionalBinding = $false)]
param(
    [string[]] $Backend = @("all"),
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

function ConvertTo-BashSingleQuoted {
    param([Parameter(Mandatory = $true)] [string] $Value)
    $singleQuote = [char]39
    $escaped = $Value.Replace([string] $singleQuote, "$singleQuote\$singleQuote$singleQuote")
    return "$singleQuote$escaped$singleQuote"
}

function Join-Csv {
    param([Parameter(Mandatory = $true)] [string[]] $Items)
    if ($Items -contains "all") {
        return "all"
    }
    return (($Items | Select-Object -Unique) -join ",")
}

function Normalize-Selection {
    param(
        [Parameter(Mandatory = $true)] [string[]] $Items,
        [Parameter(Mandatory = $true)] [string[]] $Allowed,
        [Parameter(Mandatory = $true)] [string] $Label
    )
    $selected = @()
    foreach ($item in $Items) {
        foreach ($token in ($item -split ",")) {
            $value = $token.Trim()
            if ([string]::IsNullOrWhiteSpace($value)) {
                throw "$Label vazio."
            }
            if ($value -eq "all") {
                return @("all")
            }
            if ($value -notin $Allowed) {
                throw "$Label invalido: $value. Permitidos: all,$($Allowed -join ',')"
            }
            $selected += $value
        }
    }
    return @($selected | Select-Object -Unique)
}

function Get-ReleaseTargetNames {
    param(
        [Parameter(Mandatory = $true)] [string] $RepoRoot,
        [Parameter(Mandatory = $true)] [string] $Kind,
        [Parameter(Mandatory = $true)] [string[]] $PlatformKeys
    )
    $targetFile = Join-Path $RepoRoot "dev_env\build\release_targets.json"
    if (-not (Test-Path -LiteralPath $targetFile -PathType Leaf)) {
        throw "Arquivo de targets ausente: $targetFile"
    }
    try {
        $payload = Get-Content -LiteralPath $targetFile -Raw | ConvertFrom-Json
    } catch {
        throw "Falha ao carregar targets de release: $targetFile`: $($_.Exception.Message)"
    }
    if ($payload.schema_version -ne 1) {
        throw "schema_version invalido em $targetFile"
    }
    $records = $payload.$Kind
    if ($null -eq $records) {
        throw "targets ausentes em $targetFile`: $Kind"
    }
    $names = @()
    foreach ($record in @($records | Sort-Object order)) {
        $name = [string] $record.name
        if ([string]::IsNullOrWhiteSpace($name)) {
            throw "target sem nome em $targetFile`: $Kind"
        }
        foreach ($platform in $PlatformKeys) {
            $property = $record.PSObject.Properties[$platform]
            if ($null -ne $property -and $property.Value -eq $true) {
                $names += $name
                break
            }
        }
    }
    $uniqueNames = @($names | Select-Object -Unique)
    if ($uniqueNames.Count -eq 0) {
        throw "nenhum target habilitado em $targetFile`: $Kind"
    }
    return $uniqueNames
}

Assert-Tool "git"
if (-not $SkipDebian) {
    Assert-Tool "wsl"
}

$repoRoot = Resolve-RepoRoot
$repoRootWsl = ConvertTo-WslPath $repoRoot
$repoRootWslQuoted = ConvertTo-BashSingleQuoted $repoRootWsl
$backendPlatforms = @()
if (-not $SkipWindows) {
    $backendPlatforms += "windows_amd64"
}
if (-not $SkipDebian) {
    $backendPlatforms += "debian_amd64"
}
if ($backendPlatforms.Count -eq 0) {
    $backendPlatforms = @("windows_amd64", "debian_amd64")
}
$allowedBackends = Get-ReleaseTargetNames -RepoRoot $repoRoot -Kind "backends" -PlatformKeys $backendPlatforms
$allowedDebianPackages = Get-ReleaseTargetNames -RepoRoot $repoRoot -Kind "packages" -PlatformKeys @("debian_amd64")
$backendItems = Normalize-Selection -Items $Backend -Allowed $allowedBackends -Label "backend"
$packageItems = Normalize-Selection -Items $DebianPackage -Allowed $allowedDebianPackages -Label "pacote Debian"
$backendCsv = Join-Csv $backendItems
$packageCsv = Join-Csv $packageItems
$backendCsvQuoted = ConvertTo-BashSingleQuoted $backendCsv
$packageCsvQuoted = ConvertTo-BashSingleQuoted $packageCsv

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
        "-Backend"
    )
    $windowsArgs += $backendCsv
    $windowsArgs += "-Yes"
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
        "cd $repoRootWslQuoted && bash dev_env/build/release_debian.sh --backend $backendCsvQuoted --package $packageCsvQuoted -y$(if ($DryRun) { ' --dry-run' } else { '' })"
    )
    & wsl @debianArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Release Debian falhou."
    }
}

Write-Host "Release local concluido."
