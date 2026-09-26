$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
. (Join-Path $repoRoot 'scripts\env\native_host_guard.ps1')

Assert-SsaWindowsHost -RepoRoot $repoRoot -ExpectedRoot (Get-SsaWindowsRepoRoot)
Assert-SsaWindowsVenv -VenvDir (Join-Path $repoRoot '.venv')

$previousWslInterop = $env:WSL_INTEROP
try {
    $env:WSL_INTEROP = 'blocked-test'
    $blocked = $false
    try {
        Assert-SsaWindowsHost -RepoRoot $repoRoot -ExpectedRoot (Get-SsaWindowsRepoRoot)
    }
    catch {
        $blocked = $true
    }
    if (-not $blocked) {
        throw 'native guard accepted a Windows harness launched from WSL'
    }
}
finally {
    $env:WSL_INTEROP = $previousWslInterop
}

Write-Output 'native Windows host guard tests: OK'
