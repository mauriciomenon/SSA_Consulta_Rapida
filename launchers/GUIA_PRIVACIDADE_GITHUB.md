#  GUIA DE PRIVACIDADE E GESTAO DE ARQUIVOS PESSOAIS

##  **SUA SITUACAO ATUAL**

### **Arquivos que PRECISAM ser privados:**
-  **docs_entrada/*.xlsx** - Dados sensiveis da empresa
-  **Alguns .md pessoais** - Lembretes, "nao mexer", conversas
-  **docs_saida/relatorios** - Podem conter dados sensiveis
-  **Configuracoes locais** - Especificas da sua maquina

### **Arquivos que PODEM ser publicos:**
-  **Codigo fonte** - Valor tecnico para comunidade
-  **Documentacao tecnica** - ESTRUTURA, REGRAS, CHANGELOG
-  **Scripts de build** - Uteis para outros desenvolvedores

##  **OPCOES DE PRIVACIDADE**

### **Opcao 1: Repositorio Privado (RECOMENDADA)**
```bash
# No GitHub.com:
# 1. Ir para Settings do repositorio
# 2. General → Danger Zone → Change visibility
# 3. Escolher "Private"
```

**Vantagens:**
-  Acesso apenas com sua conta GitHub
-  Sincronizacao entre suas maquinas
-  Historico completo preservado
-  Colaboracao controlada (voce escolhe quem pode ver)

**Desvantagens:**
-  Codigo tecnico nao fica disponivel para comunidade
-  Limite de repositorios privados (dependendo do plano)

### **Opcao 2: Dois Repositorios**
```bash
# Repositorio publico: SSA_Consulta_Rapida_Public
- Codigo fonte limpo
- Documentacao tecnica
- Scripts de build
- README profissional

# Repositorio privado: SSA_Consulta_Rapida_Data
- docs_entrada/
- docs_saida/
- Arquivos .md pessoais
- Configuracoes locais
```

### **Opcao 3: .gitignore Avancado + Branches**
```bash
# Branch main: Codigo publico
# Branch personal: Arquivos pessoais (nao fazer push)
```

##  **CLASSIFICACAO DOS SEUS ARQUIVOS .md**

### ** PESSOAIS (devem ser privados):**
```
*LEMBRETE*.md
*NAO_MEXER*.md
*CONVERSA*.md
*TRANSICAO*.md
TEMPLATE_NOVA_CONVERSA.md
```

### ** PROFISSIONAIS (podem ser publicos):**
```
README.md
ESTRUTURA_PROJETO.md
REGRAS_DE_OURO.md
CHANGELOG_*.md
RELEASE_*.md
BUILD_*.md
GUIA_*.md
```

##  **CONFIGURACAO RECOMENDADA**

### **1. Tornar Repositorio Privado (AGORA)**
1. Va para https://github.com/mauriciomenon/SSA_Consulta_Rapida
2. Settings → General → Danger Zone
3. Change repository visibility → Private
4. Confirmar

### **2. Atualizar .gitignore**
```gitignore
# === DADOS SENSIVEIS ===
# Arquivos de entrada (dados da empresa)
docs_entrada/

# Relatorios com dados (manter apenas templates)
docs_saida/*.xlsx
docs_saida/*.csv
docs_saida/all.*

# Arquivos pessoais (padroes)
*LEMBRETE*.md
*NAO_MEXER*.md
*CONVERSA*.md
*TRANSICAO*.md

# Configuracoes locais
.envrc
data/
logs/
```

### **3. Executar Limpeza Inteligente**
```bash
# O script atualizado perguntara sobre cada categoria
python launchers/cleanup_repository.py
```

##  **FUTURO: REPOSITORIO PUBLICO**

Se quiser disponibilizar o codigo publicamente:

### **1. Fork Publico**
```bash
# Criar fork limpo apenas com codigo
git clone --bare https://github.com/mauriciomenon/SSA_Consulta_Rapida.git ssa-public
cd ssa-public
git filter-branch --force --index-filter 'git rm --cached --ignore-unmatch docs_entrada/* docs_saida/*.xlsx' --prune-empty --tag-name-filter cat -- --all
```

### **2. README Publico**
```markdown
# SSA Consulta Rapida

Sistema profissional para consulta rapida de SSAs com:
- Interface GUI em PyQt6
- CLI robusta
- Build system multi-plataforma
- Arquitetura modular e extensivel

## Para usar com seus dados:
1. Coloque arquivos Excel em `docs_entrada/`
2. Configure `config/column_mappings.json`
3. Execute `python main.py`
```

##  **SEGURANCA DE DADOS**

### **Dados de Entrada (.xlsx)**
-  **NUNCA** committar arquivos da empresa
-  Manter apenas localmente
-  Usar .gitignore para proteger
-  Fazer backup separado (OneDrive, etc.)

### **Banco de Dados**
-  `data/ssas.db` ja esta no .gitignore
-  Fazer backup regular fora do git
-  Nao sincronizar via GitHub

### **Configuracoes Sensiveis**
-  Separar configs publicas das privadas
-  Usar variaveis de ambiente para senhas
-  Templates para configuracoes

##  **RECOMENDACAO FINAL**

### **PARA AGORA:**
1.  **Tornar repositorio privado** (5 minutos)
2.  **Executar limpeza inteligente** (10 minutos)
3.  **Atualizar .gitignore** (5 minutos)

### **PARA O FUTURO:**
1.  **Considerar repositorio publico** apenas com codigo
2.  **Melhorar documentacao** tecnica
3.  **Contribuir para comunidade** com codigo limpo

**Isso resolve sua necessidade de:**
-  Privacidade dos dados sensiveis
-  Sincronizacao entre maquinas
-  Acesso apenas com sua conta
-  Protecao automatica contra commits acidentais
