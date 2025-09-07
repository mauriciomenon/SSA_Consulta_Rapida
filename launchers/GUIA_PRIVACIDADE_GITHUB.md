# 🔒 GUIA DE PRIVACIDADE E GESTÃO DE ARQUIVOS PESSOAIS

## 🎯 **SUA SITUAÇÃO ATUAL**

### **Arquivos que PRECISAM ser privados:**
- 📊 **docs_entrada/*.xlsx** - Dados sensíveis da empresa
- 📝 **Alguns .md pessoais** - Lembretes, "não mexer", conversas
- 📈 **docs_saida/relatórios** - Podem conter dados sensíveis
- 🔧 **Configurações locais** - Específicas da sua máquina

### **Arquivos que PODEM ser públicos:**
- 💻 **Código fonte** - Valor técnico para comunidade
- 📚 **Documentação técnica** - ESTRUTURA, REGRAS, CHANGELOG
- 🔧 **Scripts de build** - Úteis para outros desenvolvedores

## 🛡️ **OPÇÕES DE PRIVACIDADE**

### **Opção 1: Repositório Privado (RECOMENDADA)**
```bash
# No GitHub.com:
# 1. Ir para Settings do repositório
# 2. General → Danger Zone → Change visibility
# 3. Escolher "Private"
```

**Vantagens:**
- ✅ Acesso apenas com sua conta GitHub
- ✅ Sincronização entre suas máquinas
- ✅ Histórico completo preservado
- ✅ Colaboração controlada (você escolhe quem pode ver)

**Desvantagens:**
- ❌ Código técnico não fica disponível para comunidade
- ❌ Limite de repositórios privados (dependendo do plano)

### **Opção 2: Dois Repositórios**
```bash
# Repositório público: SSA_Consulta_Rapida_Public
- Código fonte limpo
- Documentação técnica
- Scripts de build
- README profissional

# Repositório privado: SSA_Consulta_Rapida_Data
- docs_entrada/
- docs_saida/
- Arquivos .md pessoais
- Configurações locais
```

### **Opção 3: .gitignore Avançado + Branches**
```bash
# Branch main: Código público
# Branch personal: Arquivos pessoais (não fazer push)
```

## 📋 **CLASSIFICAÇÃO DOS SEUS ARQUIVOS .md**

### **🔒 PESSOAIS (devem ser privados):**
```
*LEMBRETE*.md
*NAO_MEXER*.md
*CAGADAS*.md
*CONVERSA*.md
*TRANSICAO*.md
TEMPLATE_NOVA_CONVERSA.md
```

### **🌍 PROFISSIONAIS (podem ser públicos):**
```
README.md
ESTRUTURA_PROJETO.md
REGRAS_DE_OURO.md
CHANGELOG_*.md
RELEASE_*.md
BUILD_*.md
GUIA_*.md
```

## 🔧 **CONFIGURAÇÃO RECOMENDADA**

### **1. Tornar Repositório Privado (AGORA)**
1. Vá para https://github.com/mauriciomenon/SSA_Consulta_Rapida
2. Settings → General → Danger Zone
3. Change repository visibility → Private
4. Confirmar

### **2. Atualizar .gitignore**
```gitignore
# === DADOS SENSÍVEIS ===
# Arquivos de entrada (dados da empresa)
docs_entrada/

# Relatórios com dados (manter apenas templates)
docs_saida/*.xlsx
docs_saida/*.csv
docs_saida/all.*

# Arquivos pessoais (padrões)
*LEMBRETE*.md
*NAO_MEXER*.md
*CAGADAS*.md
*CONVERSA*.md
*TRANSICAO*.md

# Configurações locais
.envrc
data/
logs/
```

### **3. Executar Limpeza Inteligente**
```bash
# O script atualizado perguntará sobre cada categoria
python launchers/cleanup_repository.py
```

## 🚀 **FUTURO: REPOSITÓRIO PÚBLICO**

Se quiser disponibilizar o código publicamente:

### **1. Fork Público**
```bash
# Criar fork limpo apenas com código
git clone --bare https://github.com/mauriciomenon/SSA_Consulta_Rapida.git ssa-public
cd ssa-public
git filter-branch --force --index-filter 'git rm --cached --ignore-unmatch docs_entrada/* docs_saida/*.xlsx' --prune-empty --tag-name-filter cat -- --all
```

### **2. README Público**
```markdown
# SSA Consulta Rápida

Sistema profissional para consulta rápida de SSAs com:
- Interface GUI em PyQt6
- CLI robusta
- Build system multi-plataforma
- Arquitetura modular e extensível

## Para usar com seus dados:
1. Coloque arquivos Excel em `docs_entrada/`
2. Configure `config/column_mappings.json`
3. Execute `python main.py`
```

## 🔐 **SEGURANÇA DE DADOS**

### **Dados de Entrada (.xlsx)**
- ✅ **NUNCA** committar arquivos da empresa
- ✅ Manter apenas localmente
- ✅ Usar .gitignore para proteger
- ✅ Fazer backup separado (OneDrive, etc.)

### **Banco de Dados**
- ✅ `data/ssas.db` já está no .gitignore
- ✅ Fazer backup regular fora do git
- ✅ Não sincronizar via GitHub

### **Configurações Sensíveis**
- ✅ Separar configs públicas das privadas
- ✅ Usar variáveis de ambiente para senhas
- ✅ Templates para configurações

## 💡 **RECOMENDAÇÃO FINAL**

### **PARA AGORA:**
1. ✅ **Tornar repositório privado** (5 minutos)
2. ✅ **Executar limpeza inteligente** (10 minutos)
3. ✅ **Atualizar .gitignore** (5 minutos)

### **PARA O FUTURO:**
1. 🔄 **Considerar repositório público** apenas com código
2. 📚 **Melhorar documentação** técnica
3. 🌍 **Contribuir para comunidade** com código limpo

**Isso resolve sua necessidade de:**
- 🔒 Privacidade dos dados sensíveis
- 🔄 Sincronização entre máquinas
- 👤 Acesso apenas com sua conta
- 🛡️ Proteção automática contra commits acidentais
