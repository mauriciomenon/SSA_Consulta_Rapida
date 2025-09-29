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
        Write-Host "Falha ao ler $path: $_" -ForegroundColor Yellow
        return
    }

    # Remove emoji ranges: pictographs, emoticons, transport/map, misc symbols, dingbats
    $clean = $text -replace '[\u{1F300}-\u{1F5FF}\u{1F600}-\u{1F64F}\u{1F680}-\u{1F6FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]',''
    if ($clean -ne $text) {
        Write-Host "Limpando emojis em: $path"
        $clean | Set-Content -LiteralPath $path -Encoding UTF8
    }
}

Write-Host "Concluído. Verifique alterações com 'git status' e 'git diff'."