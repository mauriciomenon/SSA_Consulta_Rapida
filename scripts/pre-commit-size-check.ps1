# Pre-commit size check: blocks files larger than 99MB
param()

$maxSizeBytes = 99MB

# Get staged files
$staged = git diff --cached --name-only
if (-not $staged) { exit 0 }

$tooLarge = @()
foreach ($file in $staged) {
  if (Test-Path $file) {
    $size = (Get-Item $file).Length
    if ($size -gt $maxSizeBytes) { $tooLarge += @{ File=$file; Size=$size } }
  }
}

if ($tooLarge.Count -gt 0) {
  Write-Host "Commit bloqueado: arquivos acima de 99MB:" -ForegroundColor Red
  foreach ($f in $tooLarge) {
    $mb = [math]::Round($f.Size / 1MB, 2)
    Write-Host (" - {0} ({1} MB)" -f $f.File, $mb)
  }
  Write-Host "Remova-os do commit ou use artefatos externos." -ForegroundColor Yellow
  exit 1
}
exit 0
