# 🚫 ARQUIVOS QUE NÃO DEVEM IR PARA O GIT

## ⚠️ PROBLEMA IDENTIFICADO E CORRIGIDO

### **data/file_cache.json** 
- **O que é:** Cache de checksums (hashes) de arquivos Excel importados
- **Por que existia no git:** Foi commitado por engano anteriormente
- **Por que não deve estar:** Arquivo temporário que muda constantemente
- **Status:** ✅ REMOVIDO do git em 07/09/2025

## 📋 TIPOS DE ARQUIVO QUE NÃO DEVEM IR PARA O GIT

### **1. Arquivos de Cache**
```
data/file_cache.json          # Cache de checksums de imports
**/__pycache__/              # Cache Python
*.pyc, *.pyo                 # Bytecode Python
.pytest_cache/               # Cache de testes
```

### **2. Dados Temporários**
```
data/ssas.db                 # Banco de dados local
data/*.backup_*              # Backups automáticos
data/historico_backups/      # Histórico de backups
logs/                        # Logs da aplicação
```

### **3. Artefatos de Build**
```
launchers/dist/              # Executáveis compilados
launchers/dist_simple/       # Builds de desenvolvimento
launchers/platforms/*/venv/  # Ambientes virtuais
build/, dist/                # Artefatos PyInstaller
```

### **4. Arquivos de Sistema**
```
.DS_Store                    # macOS
Thumbs.db                    # Windows
*.tmp, *.temp               # Temporários
.envrc                      # Configuração direnv local
```

### **5. Documentos de Trabalho**
```
docs_entrada/               # Arquivos Excel de entrada
docs_saida/                 # Relatórios gerados
exportacao/                 # Exports temporários
```

## 🛡️ PROTEÇÕES IMPLEMENTADAS

### **.gitignore Atualizado**
```gitignore
# Cache de arquivos
data/file_cache.json

# Executaveis compilados
launchers/dist/
launchers/dist_simple/

# Logs de build
launchers/logs/

# Backups automaticos de banco
data/*.backup_*
data/historico_backups/

# Arquivos de sistema
.DS_Store
Thumbs.db
```

### **Limpeza Automática**
- `--cleanup-online`: Remove arquivos indevidos do git
- `cleanup_emergency.py`: Limpeza de emergência
- Build system com proteções automáticas

## 🔍 COMO VERIFICAR

### **Verificar arquivos sendo rastreados indevidamente:**
```bash
# Listar arquivos de cache no git
git ls-files | grep -E "\.(cache|log|tmp|temp)$"

# Verificar pasta data
git ls-files data/

# Procurar arquivos grandes (possíveis executáveis)
git ls-files | xargs ls -lSr | tail -10
```

### **Verificar .gitignore funcionando:**
```bash
# Testar se arquivo está ignorado
git check-ignore -v data/file_cache.json

# Ver status sem arquivos ignorados
git status --ignored
```

## 🧹 COMO LIMPAR

### **Se arquivo indevido aparecer no git:**
```bash
# Remover do git mas manter no disco
git rm --cached nome_do_arquivo

# Limpeza automática
python launchers/cleanup_emergency.py

# Limpeza online
python launchers/build_multiplatform.py --cleanup-online
```

### **Verificar antes de commit:**
```bash
# Ver o que vai ser commitado
git status --porcelain

# Verificar tamanho dos arquivos
git diff --cached --stat

# Verificar se há arquivos binários grandes
git diff --cached --numstat | awk '$1 == "-" || $2 == "-"'
```

## 📝 REGRAS DE OURO

### **✅ SEMPRE committar:**
- Código fonte (*.py, *.md)
- Configurações (config/*.json)
- Scripts de build (launchers/*.py)
- Documentação (docs/*.md)
- Requirements e setup (requirements.txt, pyproject.toml)

### **🚫 NUNCA committar:**
- Dados locais (data/*)
- Executáveis (launchers/dist/*)
- Logs (*.log, logs/*)
- Cache (file_cache.json, __pycache__/)
- Temporários (*.tmp, *.temp)

## 🎯 RESUMO DO PROBLEMA file_cache.json

**ANTES:**
- ❌ `data/file_cache.json` estava sendo rastreado pelo git
- ❌ Arquivo de 15KB com hashes de arquivos Excel
- ❌ Mudava constantemente a cada import
- ❌ Poluía o histórico do git

**DEPOIS:**
- ✅ Removido do git com `git rm --cached`
- ✅ Protegido no `.gitignore` 
- ✅ Limpeza automática implementada
- ✅ Documentação criada para evitar reincidência

**RESULTADO:** Repositório mais limpo e profissional! 🚀
