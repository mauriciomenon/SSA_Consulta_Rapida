# Organizacao de Scripts - SSA Consulta Rapida

## Scripts Criados Recentemente

### launchers/
- cleanup_repository_complete.py (complexo, com emojis)
- cleanup_manual.py (simples, sem emojis)
- GUIA_PRIVACIDADE_GITHUB.md (com emojis)
- GUIA_PRIVACIDADE_IMPLEMENTACAO.md (com emojis)
- GUIA_PRIVACIDADE_IMPLEMENTACAO_LIMPO.md (sem emojis)

### Limpeza Necessaria

#### Scripts Duplicados
1. Manter apenas: cleanup_manual.py
2. Remover: cleanup_repository_complete.py, cleanup_repository.py
3. Manter apenas: GUIA_PRIVACIDADE_IMPLEMENTACAO_LIMPO.md
4. Remover outros guias com emojis

#### Arquivos para Organizar
- ARQUIVOS_NAO_COMMITTAR.md (mover para docs/)
- build_multiplatform.py (ja organizado)
- Varios scripts de teste antigos

## Plano de Acao

### 1. Executar Limpeza
```bash
python launchers/cleanup_manual.py
```

### 2. Organizar Scripts
```bash
# Remover scripts duplicados
rm launchers/cleanup_repository_complete.py
rm launchers/cleanup_repository.py
rm launchers/GUIA_PRIVACIDADE_GITHUB.md
rm launchers/GUIA_PRIVACIDADE_IMPLEMENTACAO.md

# Mover documentacao
mv launchers/ARQUIVOS_NAO_COMMITTAR.md docs/
mv launchers/GUIA_PRIVACIDADE_IMPLEMENTACAO_LIMPO.md docs/
```

### 3. Tornar Repositorio Privado
1. GitHub.com > Settings
2. Danger Zone > Change repository visibility
3. Make Private

### 4. Commit Final
```bash
git add .
git commit -m "feat: organizar scripts e documentacao"
git push origin main
```

## Resultado Final

### launchers/ (limpo)
- build_multiplatform.py
- cleanup_manual.py
- platforms/

### docs/ (organizado)  
- GUIA_PRIVACIDADE_IMPLEMENTACAO_LIMPO.md
- ARQUIVOS_NAO_COMMITTAR.md
- (documentacao existente)

### .gitignore (atualizado)
- Protege dados sensiveis
- Bloqueia relatorios temporarios
- Previne builds desnecessarios
