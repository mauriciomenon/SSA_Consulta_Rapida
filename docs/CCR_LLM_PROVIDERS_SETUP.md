# Claude Code Router (CCR) e Provedores LLM - Documentacao Completa

Data: 27/11/2025
Status: Todos os arquivos validados - sintaxe OK
Nota (2026-03-09): este documento e snapshot historico de setup local no Windows.
Referencias a `.github/instructions/*.instructions.md` sao legadas e podem nao
existir no estado atual deste repo.

---

## LISTA GERAL DE ARQUIVOS CRIADOS

| # | Tipo | Arquivo | Caminho Completo |
|---|------|---------|------------------|
| 1 | CCR Config | config.json | C:\Users\menon\.claude-code-router\config.json |
| 2 | Provider | zai_config.json | C:\Users\menon\git\SSA_Consulta_Rapida\config\llm_providers\zai_config.json |
| 3 | Provider | gemini_config.json | C:\Users\menon\git\SSA_Consulta_Rapida\config\llm_providers\gemini_config.json |
| 4 | Provider | openai_config.json | C:\Users\menon\git\SSA_Consulta_Rapida\config\llm_providers\openai_config.json |
| 5 | Provider | deepseek_config.json | C:\Users\menon\git\SSA_Consulta_Rapida\config\llm_providers\deepseek_config.json |
| 6 | Provider | qwen_config.json | C:\Users\menon\git\SSA_Consulta_Rapida\config\llm_providers\qwen_config.json |
| 7 | Provider | anthropic_config.json | C:\Users\menon\git\SSA_Consulta_Rapida\config\llm_providers\anthropic_config.json |
| 8 | Provider | mistral_config.json | C:\Users\menon\git\SSA_Consulta_Rapida\config\llm_providers\mistral_config.json |
| 9 | Provider | groq_config.json | C:\Users\menon\git\SSA_Consulta_Rapida\config\llm_providers\groq_config.json |
| 10 | Provider | ollama_config.json | C:\Users\menon\git\SSA_Consulta_Rapida\config\llm_providers\ollama_config.json |
| 11 | Provider Doc | README.md | C:\Users\menon\git\SSA_Consulta_Rapida\config\llm_providers\README.md |
| 12 | Instrucao | kluster-code-verify.instructions.md (repo atual) | C:\Users\menon\git\SSA_Consulta_Rapida\.github\instructions\kluster-code-verify.instructions.md |
| 13 | Documentacao | CCR_LLM_PROVIDERS_SETUP.md | C:\Users\menon\git\SSA_Consulta_Rapida\docs\CCR_LLM_PROVIDERS_SETUP.md |

### Arquivos Sincronizados para VS Code Insiders

| Tipo | Origem | Destino |
|------|--------|---------|
| mcp.json | %APPDATA%\Code\User\mcp.json | %APPDATA%\Code - Insiders\User\mcp.json |
| Instructions (16) | .github\instructions\*.instructions.md | %APPDATA%\Code - Insiders\User\instructions\*.instructions.md |

---

## Resumo da Configuracao

| Item | Status | Detalhes |
|------|--------|----------|
| CCR | Instalado | v1.0.71 |
| Config CCR | OK | 10 provedores |
| Provider JSONs | OK | 9 arquivos |
| mcp.json VS Code | OK | 19 servidores |
| mcp.json Insiders | OK | 19 servidores |

---

## 1. ARQUIVOS CRIADOS - LOCALIZACAO EXATA

### 1.1 Configuracao Principal do CCR

**Arquivo:** `C:\Users\menon\.claude-code-router\config.json`

**Conteudo:** Configuracao do router com 10 provedores LLM

**Provedores configurados:**
- Z.AI (GLM-4.5, GLM-4.6, CodeGeeX-4)
- AIHubMix (proxy para multiplos modelos)
- Google Gemini (2.0-flash, 1.5-pro)
- OpenAI (GPT-4o, o1, o3)
- DeepSeek (Coder, Reasoner R1)
- Qwen/Alibaba (Coder Plus, Max)
- Anthropic (Claude Sonnet 4, Opus 4)
- Groq (Llama 3.3-70B)
- Mistral (Codestral, Large)
- Ollama (modelos locais)

**Link direto (Windows):**
```
explorer "C:\Users\menon\.claude-code-router"
```

---

### 1.2 Arquivos de Configuracao por Provedor

**Diretorio:** `C:\Users\menon\git\SSA_Consulta_Rapida\config\llm_providers\`

| Arquivo | Tamanho | Provedor | Modelos Principais |
|---------|---------|----------|-------------------|
| `zai_config.json` | 3.5 KB | Z.AI / Zhipu | glm-4.5, glm-4.6, codegeex-4 |
| `gemini_config.json` | 3.4 KB | Google | gemini-2.0-flash, gemini-1.5-pro |
| `openai_config.json` | 4.0 KB | OpenAI | gpt-4o, o1-preview, o3-mini |
| `deepseek_config.json` | 2.8 KB | DeepSeek | deepseek-coder, deepseek-reasoner |
| `qwen_config.json` | 4.3 KB | Alibaba | qwen-coder-plus, qwen-max |
| `anthropic_config.json` | 3.5 KB | Anthropic | claude-sonnet-4, claude-opus-4 |
| `mistral_config.json` | 3.2 KB | Mistral AI | codestral-latest, mistral-large |
| `groq_config.json` | 3.3 KB | Groq | llama-3.3-70b-versatile |
| `ollama_config.json` | 4.9 KB | Ollama | qwen2.5-coder:32b (local) |
| `README.md` | 2.9 KB | - | Documentacao |

**Link direto (Windows):**
```
explorer "C:\Users\menon\git\SSA_Consulta_Rapida\config\llm_providers"
```

---

### 1.3 Arquivo de Instrucoes para Copilot

**Arquivo:** `C:\Users\menon\git\SSA_Consulta_Rapida\.github\instructions\kluster-code-verify.instructions.md`

**Proposito:** Instrucoes automaticas para o Copilot sobre uso do CCR

**Link direto (Windows):**
```
explorer "C:\Users\menon\git\SSA_Consulta_Rapida\.github\instructions"
```

---

### 1.4 Arquivos mcp.json do VS Code

**VS Code (estavel):**
```
C:\Users\menon\AppData\Roaming\Code\User\mcp.json
```

**VS Code Insiders:**
```
C:\Users\menon\AppData\Roaming\Code - Insiders\User\mcp.json
```

**Link direto (Windows):**
```
explorer "%APPDATA%\Code\User"
explorer "%APPDATA%\Code - Insiders\User"
```

---

## 2. COMO USAR O CCR

### 2.1 Comandos Basicos

```powershell
# Iniciar o servidor CCR
ccr start

# Parar o servidor
ccr stop

# Ver status
ccr status

# Reiniciar
ccr restart

# Selecionar modelo interativamente
ccr model

# Abrir interface web
ccr ui
```

### 2.2 Trocar de Provedor/Modelo

```powershell
# Usar Z.AI (sua assinatura)
ccr use zai/glm-4.5

# Usar DeepSeek (barato e bom)
ccr use deepseek/deepseek-coder

# Usar Qwen (contexto longo)
ccr use qwen/qwen-coder-plus

# Usar modelo local (Ollama)
ccr use ollama/qwen2.5-coder:32b

# Usar Gemini (multimodal)
ccr use gemini/gemini-2.0-flash-exp
```

### 2.3 Variaveis de Ambiente Necessarias

Adicione ao seu perfil PowerShell (`$PROFILE`):

```powershell
# Z.AI
$env:ZAI_API_KEY = "sua-chave-aqui"

# DeepSeek
$env:DEEPSEEK_API_KEY = "sua-chave-aqui"

# Qwen (DashScope)
$env:DASHSCOPE_API_KEY = "sua-chave-aqui"

# Google Gemini
$env:GOOGLE_API_KEY = "sua-chave-aqui"

# OpenAI
$env:OPENAI_API_KEY = "sua-chave-aqui"

# Anthropic
$env:ANTHROPIC_API_KEY = "sua-chave-aqui"

# Mistral
$env:MISTRAL_API_KEY = "sua-chave-aqui"

# Groq
$env:GROQ_API_KEY = "sua-chave-aqui"
```

---

## 3. RECOMENDACOES POR TAREFA

| Tarefa | Provedor Recomendado | Modelo | Motivo |
|--------|---------------------|--------|--------|
| Codigo simples | DeepSeek | deepseek-coder | Barato e eficiente |
| Codigo complexo | Qwen | qwen-coder-plus | Alta capacidade |
| Raciocinio | DeepSeek | deepseek-reasoner | Competidor do o1 |
| Velocidade | Groq | llama-3.3-70b | Inferencia ultra-rapida |
| Local/Offline | Ollama | qwen2.5-coder:32b | Sem custo, privacidade |
| Multimodal | Gemini | gemini-2.0-flash | Visao + audio |
| Contexto longo | Gemini | gemini-1.5-pro | 2M tokens |
| Referencia | Anthropic | claude-sonnet-4 | Qualidade Claude |

---

## 4. ESTRUTURA COMPLETA DE ARQUIVOS

```
C:\Users\menon\
|
+-- .claude-code-router\
|   +-- config.json                    <-- Config principal CCR (10 provedores)
|
+-- AppData\Roaming\
|   +-- Code\User\
|   |   +-- mcp.json                   <-- VS Code estavel (19 servidores MCP)
|   |
|   +-- Code - Insiders\User\
|       +-- mcp.json                   <-- VS Code Insiders (19 servidores MCP)
|
+-- git\SSA_Consulta_Rapida\
    |
    +-- config\llm_providers\
    |   +-- README.md                  <-- Documentacao dos provedores
    |   +-- zai_config.json            <-- Z.AI config
    |   +-- gemini_config.json         <-- Google Gemini config
    |   +-- openai_config.json         <-- OpenAI config
    |   +-- deepseek_config.json       <-- DeepSeek config
    |   +-- qwen_config.json           <-- Qwen/Alibaba config
    |   +-- anthropic_config.json      <-- Anthropic config
    |   +-- mistral_config.json        <-- Mistral config
    |   +-- groq_config.json           <-- Groq config
    |   +-- ollama_config.json         <-- Ollama config
    |
    +-- .github\instructions\
    |   +-- ccr_llm_providers.instructions.md   <-- Instrucoes Copilot
    |   +-- (outros 15 arquivos de instrucoes)
    |
    +-- docs\
        +-- CCR_LLM_PROVIDERS_SETUP.md <-- Este documento
```

---

## 5. VALIDACAO REALIZADA

### 5.1 Testes de Sintaxe JSON

| Arquivo | Resultado |
|---------|-----------|
| config.json (CCR) | OK - 10 provedores |
| zai_config.json | OK |
| gemini_config.json | OK |
| openai_config.json | OK |
| deepseek_config.json | OK |
| qwen_config.json | OK |
| anthropic_config.json | OK |
| mistral_config.json | OK |
| groq_config.json | OK |
| ollama_config.json | OK |
| mcp.json (Code) | OK - 19 servidores |
| mcp.json (Insiders) | OK - 19 servidores |

### 5.2 CCR

- Versao: 1.0.71
- Localizacao: `C:\Users\menon\AppData\Local\nodejs\ccr.ps1`
- Status: Instalado e funcional

---

## 6. TROUBLESHOOTING

### CCR nao inicia
```powershell
# Verificar se porta 3456 esta livre
netstat -ano | findstr 3456

# Matar processo se necessario
taskkill /F /PID <pid>

# Tentar novamente
ccr start
```

### API Key nao funciona
```powershell
# Verificar se variavel esta definida
$env:ZAI_API_KEY

# Definir no perfil permanente
notepad $PROFILE
# Adicionar: $env:ZAI_API_KEY = "sua-chave"
```

### Modelo nao encontrado
```powershell
# Listar modelos disponiveis
ccr model

# Verificar config
cat ~/.claude-code-router/config.json
```

---

## 7. LINKS UTEIS

- CCR GitHub: https://github.com/musistudio/claude-code-router
- Z.AI Console: https://open.bigmodel.cn/
- DeepSeek: https://platform.deepseek.com/
- Qwen: https://dashscope.console.aliyun.com/
- Gemini: https://aistudio.google.com/
- OpenAI: https://platform.openai.com/
- Anthropic: https://console.anthropic.com/
- Mistral: https://console.mistral.ai/
- Groq: https://console.groq.com/
- Ollama: https://ollama.ai/

---

Documento gerado automaticamente em 27/11/2025

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->

