# Script para adicionar MSVC ao PATH permanente do usuario
# Execute como: powershell -ExecutionPolicy Bypass -File setup_msvc_path.ps1

Write-Host "Configurando PATH permanente para MSVC..." -ForegroundColor Cyan

# Caminhos do MSVC e ferramentas
$msvcVersion = "14.44.35207"
$vsPath = "C:\Program Files\Microsoft Visual Studio\2022\Community"

$pathsToAdd = @(
    "$vsPath\VC\Tools\MSVC\$msvcVersion\bin\Hostx64\x64",
    "$vsPath\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja",
    "$vsPath\Common7\IDE",
    "$vsPath\MSBuild\Current\Bin"
)

# Windows Kits (find latest version)
$kitsPath = "C:\Program Files (x86)\Windows Kits\10\bin"
if (Test-Path $kitsPath) {
    $latestKit = Get-ChildItem $kitsPath | Where-Object { $_.PSIsContainer } | Sort-Object Name -Descending | Select-Object -First 1
    if ($latestKit) {
        $pathsToAdd += "$($latestKit.FullName)\x64"
        Write-Host "Windows Kit encontrado: $($latestKit.Name)" -ForegroundColor Green
    }
}

# Get current user PATH
$currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
$pathArray = $currentPath -split ";"

# Check each path
$added = @()
foreach ($path in $pathsToAdd) {
    if (Test-Path $path) {
        if ($pathArray -notcontains $path) {
            Write-Host "Adicionando: $path" -ForegroundColor Green
            $pathArray = @($path) + $pathArray  # Add at beginning to take precedence
            $added += $path
        } else {
            Write-Host "Ja existe: $path" -ForegroundColor Yellow
        }
    } else {
        Write-Host "Caminho nao existe: $path" -ForegroundColor Red
    }
}

if ($added.Count -gt 0) {
    # Update PATH
    $newPath = ($pathArray | Where-Object { $_ -ne "" }) -join ";"
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")

    Write-Host "`nPATH atualizado com sucesso!" -ForegroundColor Green
    Write-Host "Caminhos adicionados:" -ForegroundColor Cyan
    $added | ForEach-Object { Write-Host "  - $_" }

    Write-Host "`nIMPORTANTE: Feche e reabra todos os terminais para aplicar as mudancas." -ForegroundColor Yellow
    Write-Host "`nPara testar, execute em novo terminal:" -ForegroundColor Cyan
    Write-Host "  link.exe" -ForegroundColor White
    Write-Host "  cl.exe" -ForegroundColor White

} else {
    Write-Host "`nNenhuma mudanca necessaria. PATH ja configurado." -ForegroundColor Green
}

# Show current link.exe locations
Write-Host "`nLocalizacoes de link.exe no sistema:" -ForegroundColor Cyan
$env:Path -split ";" | ForEach-Object {
    $linkPath = Join-Path $_ "link.exe"
    if (Test-Path $linkPath) {
        Write-Host "  - $linkPath" -ForegroundColor White
    }
}

Write-Host "`nPressione qualquer tecla para sair..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
