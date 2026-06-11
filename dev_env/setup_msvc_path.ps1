param(
    [switch]$ApplyToCurrentSession
)

$ErrorActionPreference = "Stop"

function Write-Info {
    param([string]$Message)
    Write-Host "[msvc] $Message" -ForegroundColor Cyan
}

function Find-VcVars64 {
    $vswhere = "C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
    if (Test-Path -LiteralPath $vswhere) {
        $installPath = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
        if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($installPath)) {
            $candidate = Join-Path $installPath "VC\Auxiliary\Build\vcvars64.bat"
            if (Test-Path -LiteralPath $candidate) {
                return $candidate
            }
        }
    }

    foreach ($version in @("18", "2022", "17", "16")) {
        foreach ($edition in @("BuildTools", "Community", "Professional", "Enterprise")) {
            foreach ($root in @("C:\Program Files\Microsoft Visual Studio", "C:\Program Files (x86)\Microsoft Visual Studio")) {
                $candidate = Join-Path $root "$version\$edition\VC\Auxiliary\Build\vcvars64.bat"
                if (Test-Path -LiteralPath $candidate) {
                    return $candidate
                }
            }
        }
    }
    return $null
}

function Import-VcVarsIntoCurrentSession {
    param([Parameter(Mandatory = $true)] [string]$VcVarsPath)

    $environmentLines = & cmd.exe /d /s /c "`"$VcVarsPath`" >nul && set"
    if ($LASTEXITCODE -ne 0) {
        throw "vcvars64.bat failed: $VcVarsPath"
    }
    foreach ($line in $environmentLines) {
        $separator = $line.IndexOf("=")
        if ($separator -le 0) {
            continue
        }
        $name = $line.Substring(0, $separator)
        $value = $line.Substring($separator + 1)
        Set-Item -Path "Env:$name" -Value $value
    }
}

Write-Info "MSVC diagnostic mode. This script does not modify the user PATH."
$vcvars = Find-VcVars64
if ([string]::IsNullOrWhiteSpace($vcvars)) {
    Write-Error "vcvars64.bat not found. Install Visual Studio Build Tools with the C++ workload."
    exit 1
}

Write-Info "vcvars64.bat: $vcvars"
if ($ApplyToCurrentSession) {
    Import-VcVarsIntoCurrentSession -VcVarsPath $vcvars
    Write-Info "MSVC variables imported into the current PowerShell session only."
    Write-Info "cl.exe: $((Get-Command cl.exe -ErrorAction SilentlyContinue).Source)"
    Write-Info "link.exe: $((Get-Command link.exe -ErrorAction SilentlyContinue).Source)"
} else {
    Write-Info "To import MSVC variables into this shell, rerun with -ApplyToCurrentSession."
    Write-Info "Build scripts use vswhere/vcvars64.bat directly and do not require permanent PATH edits."
}
