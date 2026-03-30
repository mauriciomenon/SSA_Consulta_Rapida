# LLM Providers Configuration

Este diretorio contem configuracoes de referencia para varios provedores de LLM que podem ser usados com:
- **Claude Code Router (CCR)** - Roteamento de requisicoes para diferentes provedores
- **Aplicacoes locais** - Configuracao direta
- **VS Code extensions** - Cline, Continue.dev, etc.

## Provedores Configurados

| Provedor | Arquivo | Uso Principal |
|----------|---------|---------------|
| Z.AI (Zhipu) | `zai_config.json` | GLM-4.5/4.6, CodeGeeX |
| Google Gemini | `gemini_config.json` | Gemini 2.0, 1.5 Pro/Flash |
| OpenAI | `openai_config.json` | GPT-4o, o1/o3, Codex |
| DeepSeek | `deepseek_config.json` | DeepSeek Coder, R1 |
| Qwen | `qwen_config.json` | Qwen Coder, Qwen Max |
| Anthropic | `anthropic_config.json` | Claude Opus/Sonnet |
| Mistral | `mistral_config.json` | Codestral, Mistral Large |
| Groq | `groq_config.json` | Llama 3.3, inferencia rapida |
| Ollama | `ollama_config.json` | Modelos locais |

## Estrutura dos Arquivos

Cada arquivo JSON contem:
- `provider`: Informacoes do provedor (site, docs, pricing)
- `api`: Configuracao de API (URLs, autenticacao)
- `models`: Lista de modelos disponiveis com capacidades
- `ccr_config`: Configuracao pronta para Claude Code Router
- `environment_variables`: Variaveis de ambiente necessarias
- `notes`: Dicas e observacoes

## Uso com CCR

O arquivo `~/.claude-code-router/config.json` foi configurado com todos os provedores.
Para usar, edite e adicione suas chaves de API:

```json
{
  "Providers": [
    {
      "name": "zai",
      "api_base_url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
      "api_key": "SUA_CHAVE_AQUI",
      "models": ["glm-4.5", "glm-4.6"]
    }
  ]
}
```

## Comparacao de Modelos para Codigo

| Modelo | Provedor | Contexto | Custo | Nota |
|--------|----------|----------|-------|------|
| Qwen 2.5 Coder 32B | Qwen/Ollama | 128K | Gratis local | Open source |
| DeepSeek Coder | DeepSeek | 128K | Baixo | Excelente custo-beneficio |
| CodeGeeX-4 | Z.AI | 128K | Medio | Muito bom para codigo |
| Codestral | Mistral | 32K | Medio | Especializado |
| GPT-4o | OpenAI | 128K | Alto | Muito capaz |
| Claude Sonnet 4 | Anthropic | 200K | Alto | Contexto grande |

## Recomendacoes

1. **Para desenvolvimento diario**: DeepSeek Coder ou Qwen Coder (custo-beneficio)
2. **Para tarefas complexas**: Claude Sonnet 4 ou GPT-4o
3. **Para raciocinio**: DeepSeek R1 ou o1
4. **Para velocidade**: Groq com Llama 3.3
5. **Para rodar local**: Ollama + Qwen 2.5 Coder

## Variaveis de Ambiente

Crie um arquivo `.env` ou configure no sistema:

```bash
# Z.AI
ZAI_API_KEY=sua_chave

# Google
GOOGLE_API_KEY=sua_chave

# OpenAI
OPENAI_API_KEY=sua_chave

# DeepSeek
DEEPSEEK_API_KEY=sua_chave

# Alibaba (Qwen)
DASHSCOPE_API_KEY=sua_chave

# Anthropic
ANTHROPIC_API_KEY=sua_chave

# Mistral
MISTRAL_API_KEY=sua_chave

# Groq
GROQ_API_KEY=sua_chave
```

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->

