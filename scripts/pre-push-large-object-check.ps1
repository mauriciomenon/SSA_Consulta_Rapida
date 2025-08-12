# Pre-push hook: block pushes that introduce large (> 99 MB) Git objects
# Usage: copy this file to .git/hooks/pre-push and make it executable.
# PowerShell script; designed for Windows environments.

param()

$ErrorActionPreference = 'Stop'

# Size limit in bytes (99 MB)
$sizeLimit = 99MB

function Get-UpstreamRefOrNull {
    try {
        $upstream = git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>$null
        if ($LASTEXITCODE -eq 0 -and $upstream) { return $upstream.Trim() }
        return $null
    } catch { return $null }
}

function Get-ObjectsToCheck($upstreamRef) {
    if ($null -ne $upstreamRef -and $upstreamRef) {
        # Only new commits relative to upstream
        $range = "$upstreamRef..HEAD"
        git rev-list --objects $range | ForEach-Object { ($_ -split ' ')[0] } | Where-Object { $_ }
    } else {
        # No upstream (first push) – scan recent history to be safe
        git rev-list --objects HEAD | ForEach-Object { ($_ -split ' ')[0] } | Where-Object { $_ }
    }
}

function Get-LargeObjects($objectIds) {
    $large = @()
    foreach ($oid in $objectIds) {
        try {
            $size = [int64](git cat-file -s $oid 2>$null)
            if ($size -ge $sizeLimit) {
                $large += [pscustomobject]@{ Id = $oid; Size = $size }
            }
        } catch { }
    }
    return $large
}

try {
    $upstream = Get-UpstreamRefOrNull
    $objectIds = Get-ObjectsToCheck -upstreamRef $upstream | Select-Object -Unique
    $largeObjects = Get-LargeObjects -objectIds $objectIds

    if ($largeObjects.Count -gt 0) {
        Write-Host "❌ Push bloqueado: objetos grandes encontrados (>= 99 MB):" -ForegroundColor Red
        foreach ($o in $largeObjects) {
            $mb = [Math]::Round($o.Size / 1MB, 2)
            Write-Host ("  - {0} -> {1} MB" -f $o.Id, $mb) -ForegroundColor Yellow
        }
        Write-Host "Remova/reescreva o histórico (git filter-repo) ou use Git LFS antes de tentar novamente." -ForegroundColor Yellow
        exit 1
    }

    exit 0
} catch {
    # On failure, do not block push, but warn
    Write-Host "Aviso: falha ao verificar tamanhos de objetos. Prosseguindo com o push." -ForegroundColor Yellow
    exit 0
}
