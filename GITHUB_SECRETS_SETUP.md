# GUIA DE CONFIGURACAO SEGURA - GITHUB SECRETS

**Data:** 2025-12-01
**Repositorio:** SSA_Consulta_Rapida
**Status:** Aguardando configuracao manual

---

## 1. ACESSO A INTERFACE DE SECRETS

### Passo a Passo:

1. Acesse: https://github.com/seu-usuario/SSA_Consulta_Rapida/settings/secrets/actions
2. Ou navegue manualmente:
   - Abra o repositorio no GitHub
   - Clique em **Settings** (canto superior direito)
   - No menu lateral esquerdo: **Secrets and variables** > **Actions**

---

## 2. SECRETS NECESSARIOS

### 2.1 SNYK_TOKEN (Prioritario)

**Service:** Snyk Security Scanning
**Workflow:** [.github/workflows/snyk.yml](.github/workflows/snyk.yml)

**Como obter o token:**
1. Acesse: https://app.snyk.io/account
2. Va para: **Auth Tokens** ou **API Tokens**
3. Clique em: **Generate token** ou **Create new token**
4. Nome sugerido: `GitHub Actions - SSA_Consulta_Rapida`
5. Copie o token gerado (formato: `XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX`)

**Como adicionar no GitHub:**
1. No GitHub Secrets page, clique: **New repository secret**
2. Name: `SNYK_TOKEN`
3. Secret: Cole o token do Snyk (CTRL+V)
4. Clique: **Add secret**

**IMPORTANTE:** O token so e exibido UMA VEZ. Se perder, gere um novo.

---

### 2.2 SONAR_TOKEN (Opcional)

**Service:** SonarCloud Code Quality
**Workflow:** [.github/workflows/sonarcloud.yml](.github/workflows/sonarcloud.yml)

**Como obter o token:**
1. Acesse: https://sonarcloud.io
2. Faca login (pode usar conta GitHub)
3. Va para: **My Account** > **Security**
4. Gere um novo token:
   - Name: `GitHub Actions - SSA_Consulta_Rapida`
   - Type: `User Token`
5. Copie o token gerado

**Como adicionar no GitHub:**
1. No GitHub Secrets page, clique: **New repository secret**
2. Name: `SONAR_TOKEN`
3. Secret: Cole o token do SonarCloud
4. Clique: **Add secret**

**NOTA:** SonarCloud tambem requer configuracao de projeto. Veja Secao 3.

---

## 3. CONFIGURACAO ADICIONAL - SONARCLOUD

Alem do token, SonarCloud precisa de um projeto configurado:

### 3.1 Criar Projeto no SonarCloud

1. Acesse: https://sonarcloud.io/projects/create
2. Escolha: **GitHub** como source
3. Selecione: `SSA_Consulta_Rapida`
4. Configure:
   - Project Key: (gerado automaticamente ou customize)
   - Organization: (sua organization no SonarCloud)

### 3.2 Criar arquivo sonar-project.properties

**Conteudo necessario:**
```properties
sonar.projectKey=SEU_PROJECT_KEY
sonar.organization=SUA_ORGANIZATION

# Metadata
sonar.projectName=SSA Consulta Rapida
sonar.projectVersion=1.0

# Source directories
sonar.sources=core,armazenamento,processamento
sonar.tests=tests

# Python specific
sonar.python.version=3.13

# Exclusions
sonar.exclusions=**/launchers/**,**/dist/**,**/build/**,**/__pycache__/**
```

**NOTA:** Substitua `SEU_PROJECT_KEY` e `SUA_ORGANIZATION` pelos valores reais.

---

## 4. REATIVACAO DOS WORKFLOWS

Apos configurar os secrets, edite os workflows para reativa-los:

### 4.1 Snyk Security

**Arquivo:** [.github/workflows/snyk.yml](.github/workflows/snyk.yml)

**Alteracao necessaria:**
```yaml
# ANTES (linha 5-6):
on:
  workflow_dispatch:

# DEPOIS:
on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]
  workflow_dispatch:
```

### 4.2 SonarCloud

**Arquivo:** [.github/workflows/sonarcloud.yml](.github/workflows/sonarcloud.yml)

**Alteracao necessaria:**
```yaml
# ANTES (linha 5-6):
on:
  workflow_dispatch:

# DEPOIS:
on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]
  workflow_dispatch:
```

---

## 5. VALIDACAO DOS SECRETS

Apos configurar, valide que os secrets estao visiveis:

1. Acesse: https://github.com/seu-usuario/SSA_Consulta_Rapida/settings/secrets/actions
2. Verifique que aparecem:
   - `SNYK_TOKEN` (com data de criacao)
   - `SONAR_TOKEN` (se configurado)

**IMPORTANTE:** Voce NAO consegue visualizar o valor dos secrets depois de salvos (seguranca).

---

## 6. TESTE DOS WORKFLOWS

### Teste Manual (Recomendado):

**Via GitHub UI:**
1. Va para: **Actions** tab no GitHub
2. Selecione workflow: **Snyk Security** ou **SonarCloud**
3. Clique: **Run workflow** > **Run workflow**
4. Acompanhe a execucao

**Via CLI (gh):**
```bash
# Testar Snyk
gh workflow run snyk.yml

# Testar SonarCloud
gh workflow run sonarcloud.yml

# Ver resultados
gh run list --limit 5
```

### Teste Automatico (Apos reativar triggers):

Faca um commit simples e push:
```bash
# Exemplo: atualizar este documento
git add GITHUB_SECRETS_SETUP.md
git commit -m "docs: add GitHub secrets setup guide"
git push origin main
```

Workflows devem executar automaticamente.

---

## 7. TROUBLESHOOTING

### Erro: "Error: Snyk token is not set"

**Causa:** Secret nao configurado ou nome incorreto
**Solucao:** Verifique que o secret se chama exatamente `SNYK_TOKEN` (case-sensitive)

### Erro: "SonarCloud project not found"

**Causa:** Projeto nao configurado no SonarCloud
**Solucao:** Complete Secao 3 (Configuracao SonarCloud)

### Workflow nao executa automaticamente

**Causa:** Triggers ainda configurados como `workflow_dispatch` apenas
**Solucao:** Complete Secao 4 (Reativacao dos Workflows)

---

## 8. BOAS PRATICAS DE SEGURANCA

### ✅ SEMPRE:
- Use secrets do GitHub para tokens (NUNCA commite tokens no codigo)
- Revogue tokens antigos apos rotacao
- Use tokens com permissoes minimas necessarias
- Documente quando e porque um token foi criado

### ❌ NUNCA:
- Compartilhe tokens em chat, email, ou mensagens
- Commite tokens em arquivos (`.env`, `config.json`, etc)
- Use o mesmo token em multiplos projetos (gere tokens unicos)
- Deixe tokens sem uso ativos (revogue se nao usa mais)

---

## 9. ROTACAO DE TOKENS (MANUTENCAO FUTURA)

**Frequencia recomendada:** A cada 6-12 meses ou apos incidentes de seguranca

**Procedimento:**
1. Gere novo token no servico (Snyk/SonarCloud)
2. Atualize secret no GitHub (sobrescreve o antigo)
3. Execute workflow de teste para validar
4. Revogue token antigo no servico
5. Documente data da rotacao

---

## 10. PROXIMOS PASSOS

1. [ ] Configurar `SNYK_TOKEN` no GitHub Secrets
2. [ ] (Opcional) Configurar `SONAR_TOKEN` e projeto SonarCloud
3. [ ] Testar workflows manualmente via `workflow_dispatch`
4. [ ] Reativar triggers automaticos (push/pull_request)
5. [ ] Validar execucao em proximo commit
6. [ ] Deletar este documento apos configuracao completa (ou mover para docs/)

---

**Gerado em:** 2025-12-01
**Autor:** Claude Code (Assistente de Desenvolvimento)
