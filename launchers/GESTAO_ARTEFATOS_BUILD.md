# IMPORTANTE: Gestão de Artefatos de Build

## ⚠️ PROBLEMA IDENTIFICADO E RESOLVIDO

### O que aconteceu
O diretório `launchers/dist_simple/` foi criado pelo script `build_simple.py` e poderia ter sido commitado indevidamente para o repositório, causando:
- Aumento desnecessário do tamanho do repositório
- Upload de executáveis binários grandes
- Poluição do histórico do git

### ✅ SOLUÇÕES IMPLEMENTADAS

#### 1. build_simple.py corrigido
- ✅ Adicionada limpeza automática via `atexit.register()`
- ✅ Aviso claro sobre natureza temporária do `dist_simple`
- ✅ Limpeza automática ao finalizar o script

#### 2. .gitignore atualizado
- ✅ `launchers/dist_simple/` está explicitamente ignorado
- ✅ Proteção contra outros artefatos temporários

#### 3. Limpeza de emergência
- ✅ Script `cleanup_emergency.py` para casos problemáticos
- ✅ Remove `dist_simple` do filesystem e do git
- ✅ Verifica e limpa outros artefatos

#### 4. Build system principal
- ✅ Funcionalidade `--auto-cleanup` no build_multiplatform.py
- ✅ Funcionalidade `--cleanup-online` para limpeza do git
- ✅ Limpeza automática após builds bem-sucedidos

## 🚫 REGRAS DE OURO

### NUNCA committar:
- `launchers/dist/` (builds de produção)
- `launchers/dist_simple/` (builds de desenvolvimento)
- `launchers/platforms/*/venv/` (ambientes virtuais)
- `launchers/logs/` (logs de build)
- `**/__pycache__/` (cache Python)
- `build/`, `dist/` (artefatos PyInstaller)

### SEMPRE committar:
- `launchers/*.py` (scripts de build)
- `launchers/platforms/*/build_config.json` (configurações)
- `launchers/*.md` (documentação)
- `.gitignore` atualizado

## 🛠 COMANDOS ÚTEIS

### Verificação preventiva
```bash
# Antes de commit, verificar se há artefatos indevidos
git status | grep -E "(dist|build|__pycache__|\.pyc)"

# Listar arquivos grandes sendo rastreados
git ls-files | xargs ls -lSr | tail -10
```

### Limpeza de emergência
```bash
# Se dist_simple aparecer no git
python launchers/cleanup_emergency.py

# Limpeza completa online
python launchers/build_multiplatform.py --cleanup-online

# Verificar .gitignore
grep -n "dist_simple" .gitignore
```

### Build seguro
```bash
# Build de desenvolvimento (limpa automaticamente)
python launchers/build_simple.py

# Build de produção com limpeza
python launchers/build_complete.py

# Build manual com proteções
python launchers/build_multiplatform.py --auto-cleanup --cleanup-online
```

## 📋 CHECKLIST PRE-COMMIT

Antes de fazer commit, sempre verificar:

- [ ] `git status` não mostra arquivos em `dist/` ou `dist_simple/`
- [ ] Tamanho do repositório não aumentou drasticamente
- [ ] Apenas arquivos de código/configuração sendo commitados
- [ ] `.gitignore` está atualizado e funcionando

## 🔧 TROUBLESHOOTING

### Se dist_simple aparece no git:
1. Execute: `python launchers/cleanup_emergency.py`
2. Verifique: `git status --porcelain | grep dist_simple`
3. Se ainda aparecer: `git rm -r --cached launchers/dist_simple`

### Se build_simple.py não limpa:
1. Verifique se tem permissões de escrita
2. Execute manualmente: `rm -rf launchers/dist_simple`
3. Atualize o script se necessário

### Se .gitignore não funciona:
1. Arquivo já estava sendo rastreado: `git rm --cached <arquivo>`
2. Verificar sintaxe do .gitignore
3. Testar com: `git check-ignore -v <arquivo>`

## 📝 HISTÓRICO DE CORREÇÕES

- **2025-09-07**: Identificado problema com dist_simple
- **2025-09-07**: Implementada limpeza automática no build_simple.py
- **2025-09-07**: Criado cleanup_emergency.py
- **2025-09-07**: Atualizado .gitignore com proteções adicionais
- **2025-09-07**: Adicionadas funcionalidades de limpeza ao build system
