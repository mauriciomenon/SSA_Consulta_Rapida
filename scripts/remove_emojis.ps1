# Remove emojis from documentation files (md, rst, txt)
# Usage: .\scripts\remove_emojis.ps1 -Root . -Includes "*.md","*.rst","*.txt"
param(
    [string[]]$Includes = @("*.md","*.rst","*.txt","README*"),
    [string]$Root = "."
)

Write-Host "Buscando arquivos para limpar emojis em $Root ..."
Get-ChildItem -Path $Root -Recurse -File -Include $Includes | ForEach-Object {
    $path = $_.FullName
    try {
        $text = Get-Content -Raw -LiteralPath $path -ErrorAction Stop
    } catch {
        Write-Host ("Falha ao ler {0}: {1}" -f $path, $_) -ForegroundColor Yellow
        return
    }

    # Remove emoji ranges supported by the .NET regex engine.
    $emojiPattern = '[\u2600-\u27BF]|[\uD83C-\uDBFF][\uDC00-\uDFFF]'
    $clean = [regex]::Replace($text, $emojiPattern, "")
    if ($clean -ne $text) {
        Write-Host "Limpando emojis em: $path"
        $clean | Set-Content -LiteralPath $path -Encoding UTF8
    }
}

Write-Host "Concluído. Verifique alterações com 'git status' e 'git diff'."
