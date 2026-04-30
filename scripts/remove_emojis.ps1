# Remove emojis from documentation files (md, rst, txt)
# Usage: .\scripts\remove_emojis.ps1 -Root . -Includes "*.md","*.rst","*.txt","README.md","README.rst","README.txt"
param(
    [string[]]$Includes = @("*.md","*.rst","*.txt","README.md","README.rst","README.txt"),
    [string]$Root = "."
)

$utf8NoBom = [System.Text.UTF8Encoding]::new($false)

Write-Host "Buscando arquivos para limpar emojis em $Root ..."
Get-ChildItem -Path $Root -Recurse -File -Include $Includes | ForEach-Object {
    $path = $_.FullName
    try {
        $text = Get-Content -Raw -LiteralPath $path -ErrorAction Stop
    } catch {
        Write-Host ("Falha ao ler {0}: {1}" -f $path, $_) -ForegroundColor Yellow
        return
    }
    if ($null -eq $text) {
        return
    }

    # Keep ranges aligned with scripts/remove_emojis.py; only match emoji surrogate ranges.
    $emojiPattern = '[\uD83C][\uDF00-\uDFFF]|[\uD83D][\uDC00-\uDEFF]|[\uD83E][\uDD00-\uDDFF]'
    $clean = [regex]::Replace($text, $emojiPattern, "")
    if ($clean -ne $text) {
        Write-Host "Limpando emojis em: $path"
        try {
            [System.IO.File]::WriteAllText(
                $path,
                $clean,
                $utf8NoBom
            )
        } catch {
            Write-Host ("Falha ao escrever {0}: {1}" -f $path, $_) -ForegroundColor Yellow
        }
    }
}

Write-Host "Concluído. Verifique alterações com 'git status' e 'git diff'."
