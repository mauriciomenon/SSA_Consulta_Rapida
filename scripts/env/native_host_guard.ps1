function Get-SsaWindowsRepoRoot {
    if ([string]::IsNullOrWhiteSpace($env:USERPROFILE)) {
        throw "[native-guard] BLOCKED: USERPROFILE is required for the Windows harness."
    }
    return Join-Path ([IO.Path]::GetFullPath($env:USERPROFILE)) 'gitlab\ssa_consulta_rapida_pyqt6'
}

function Assert-SsaWindowsHost {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][string]$ExpectedRoot
    )

    if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
        throw "[native-guard] BLOCKED: PowerShell host is not native Windows."
    }
    if ($env:WSL_INTEROP -or $env:WSL_DISTRO_NAME) {
        throw "[native-guard] BLOCKED: Windows harness cannot be launched from WSL."
    }

    $resolvedRoot = (Resolve-Path -LiteralPath $RepoRoot -ErrorAction Stop).ProviderPath.TrimEnd('\')
    $expected = [IO.Path]::GetFullPath($ExpectedRoot).TrimEnd('\')
    if ($resolvedRoot.StartsWith('\\')) {
        throw "[native-guard] BLOCKED: UNC/WSL repository is forbidden: $resolvedRoot"
    }

    $allowed = $resolvedRoot.Equals($expected, [StringComparison]::OrdinalIgnoreCase)
    if (-not $allowed -and $env:SSA_NATIVE_GUARD_TEST_ROOT) {
        $testRoot = [IO.Path]::GetFullPath($env:SSA_NATIVE_GUARD_TEST_ROOT).TrimEnd('\')
        $tempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')
        $isTempTest = $testRoot.StartsWith($tempRoot, [StringComparison]::OrdinalIgnoreCase)
        $allowed = $isTempTest -and (
            $resolvedRoot.Equals($testRoot, [StringComparison]::OrdinalIgnoreCase) -or
            $resolvedRoot.StartsWith("$testRoot\", [StringComparison]::OrdinalIgnoreCase)
        )
    }
    if (-not $allowed) {
        throw "[native-guard] BLOCKED: Windows repo is '$resolvedRoot'; expected '$expected'."
    }

    if ($resolvedRoot.Equals($expected, [StringComparison]::OrdinalIgnoreCase)) {
        $repoItem = Get-Item -LiteralPath $resolvedRoot -Force
        if ($repoItem.Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw "[native-guard] BLOCKED: Windows repo cannot be a reparse point: $resolvedRoot"
        }
    }
}

function Test-SsaWindowsPeFile {
    param([Parameter(Mandatory = $true)][string]$Path)

    $stream = [IO.File]::OpenRead($Path)
    try {
        return ($stream.ReadByte() -eq 0x4d -and $stream.ReadByte() -eq 0x5a)
    }
    finally {
        $stream.Dispose()
    }
}

function Assert-SsaWindowsVenv {
    param([Parameter(Mandatory = $true)][string]$VenvDir)

    if (-not (Test-Path -LiteralPath $VenvDir)) {
        return
    }
    $venvItem = Get-Item -LiteralPath $VenvDir -Force
    if (-not $venvItem.PSIsContainer -or ($venvItem.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw "[native-guard] BLOCKED: invalid Windows venv: $VenvDir"
    }

    $configPath = Join-Path $VenvDir 'pyvenv.cfg'
    if (Test-Path -LiteralPath $configPath -PathType Leaf) {
        $configText = Get-Content -LiteralPath $configPath -Raw
        if ($configText -match '(?im)^(?:home|executable)\s*=\s*(?:/|\\\\wsl)') {
            throw "[native-guard] BLOCKED: Linux pyvenv.cfg found in Windows repo: $VenvDir"
        }
    }

    $pythonPath = Join-Path $VenvDir 'Scripts\python.exe'
    $activatePath = Join-Path $VenvDir 'Scripts\Activate.ps1'
    if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf) -or
        -not (Test-Path -LiteralPath $activatePath -PathType Leaf)) {
        throw "[native-guard] BLOCKED: incomplete or foreign Windows venv; quarantine it: $VenvDir"
    }
    if (-not (Test-SsaWindowsPeFile -Path $pythonPath)) {
        throw "[native-guard] BLOCKED: venv Python is not a Windows PE executable: $pythonPath"
    }
    $posixBin = Join-Path $VenvDir 'bin'
    if ((Test-Path -LiteralPath (Join-Path $posixBin 'activate')) -or
        (Test-Path -LiteralPath (Join-Path $posixBin 'python'))) {
        throw "[native-guard] BLOCKED: POSIX bin directory found in Windows venv: $VenvDir"
    }
}
