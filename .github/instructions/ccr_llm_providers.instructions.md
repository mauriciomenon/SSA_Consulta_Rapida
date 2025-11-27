---
applyTo: '**'
description: Instrucoes para uso do Claude Code Router (CCR) e provedores LLM alternativos
---

# Claude Code Router (CCR) e Provedores LLM

## O que e CCR

Claude Code Router e um roteador que permite usar diferentes provedores de LLM com ferramentas que esperam API do Claude/OpenAI.

**Instalacao:**
```bash
npm install -g @musistudio/claude-code-router
```

**Configuracao:** `~/.claude-code-router/config.json`

## Provedores Configurados

O usuario tem configuracao para os seguintes provedores:

| Provedor | Modelos Principais | Uso Ideal |
|----------|-------------------|-----------|
| Z.AI | glm-4.5, glm-4.6, codegeex-4 | Codigo, chat geral |
| DeepSeek | deepseek-coder, deepseek-reasoner | Codigo, raciocinio |
| Qwen | qwen-coder-plus, qwen-max | Codigo, contexto longo |
| Gemini | gemini-2.0-flash, gemini-1.5-pro | Multimodal, contexto 2M |
| OpenAI | gpt-4o, o1-preview | Referencia, raciocinio |
| Anthropic | claude-sonnet-4, claude-opus-4 | Contexto 200K |
| Mistral | codestral, mistral-large | Codigo eficiente |
| Groq | llama-3.3-70b | Velocidade extrema |
| Ollama | qwen2.5-coder:32b | Local, sem custo |

## Quando Mencionar CCR

- Quando usuario perguntar sobre usar diferentes LLMs
- Quando precisar de modelo mais barato que Claude/GPT
- Quando quiser rodar modelos localmente
- Quando mencionar Z.AI, DeepSeek, Qwen, etc.

## Arquivos de Configuracao

Configuracoes de cada provedor em:
`config/llm_providers/`

- `zai_config.json` - Z.AI / Zhipu AI
- `deepseek_config.json` - DeepSeek
- `qwen_config.json` - Qwen / Alibaba
- `gemini_config.json` - Google Gemini
- `openai_config.json` - OpenAI
- `anthropic_config.json` - Anthropic Claude
- `mistral_config.json` - Mistral AI
- `groq_config.json` - Groq
- `ollama_config.json` - Ollama (local)

## Uso do CCR

**Iniciar servidor:**
```bash
ccr start
```

**Trocar modelo:**
```bash
ccr use zai/glm-4.5
ccr use deepseek/deepseek-coder
ccr use ollama/qwen2.5-coder:32b
```

**Listar configuracao:**
```bash
ccr config
```

## Recomendacoes por Tarefa

| Tarefa | Modelo Recomendado | Motivo |
|--------|-------------------|--------|
| Codigo simples | DeepSeek Coder | Barato e bom |
| Codigo complexo | Qwen Coder Plus | Muito capaz |
| Raciocinio | DeepSeek R1 | Competidor do o1 |
| Velocidade | Groq Llama | Inferencia ultra-rapida |
| Local/Offline | Ollama Qwen | Sem custo, privacidade |
| Multimodal | Gemini 2.0 | Visao + audio |

## Variaveis de Ambiente

Se o usuario precisar configurar APIs:
- `ZAI_API_KEY` - Z.AI
- `DEEPSEEK_API_KEY` - DeepSeek
- `DASHSCOPE_API_KEY` - Qwen
- `GOOGLE_API_KEY` - Gemini
- `OPENAI_API_KEY` - OpenAI
- `ANTHROPIC_API_KEY` - Anthropic
- `MISTRAL_API_KEY` - Mistral
- `GROQ_API_KEY` - Groq
