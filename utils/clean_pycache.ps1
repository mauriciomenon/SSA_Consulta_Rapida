# clean_pycache.ps1
# Script para remover todas as pastas __pycache__ recursivamente a partir da raiz do projeto

# 1. Coleta todas as pastas __pycache__
$dirs = Get-ChildItem -Path . -Directory -Filter "__pycache__" -Recurse -Force

# 2. (Opcional) Exibe a lista de diretorios encontrados para revisao
$dirs.FullName | ForEach-Object { Write-Host $_ }

# 3. Remove cada diretorio sem pedirmos confirmacao
foreach ($dir in $dirs) {
    Remove-Item -Path $dir.FullName -Recurse -Force
}

# 4. Mensagem de conclusao
Write-Host "Remocao de __pycache__ concluida."