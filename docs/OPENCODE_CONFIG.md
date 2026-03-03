# OhMyOpenCode Configuration

## Configuracao Completa - Kimi 2.5 + GLM

### Provedores Configurados

1. **Kimi (Primary)**
   - Modelo: `kimi/k2.5-free`
   - Contexto: 1M tokens
   - Saida: 8K tokens
   - Variantes: high, medium, low

2. **Z.ai Coding Plan (Fallback)**
   - Modelo: `zai-coding-plan/glm-4.7`
   - Modelo: `zai-coding-plan/glm-5`
   - Contexto: 32K tokens
   - Saida: 8K tokens
   - Variantes: high, medium, low

3. **Google (Gemini - Para multimodal)**
   - Modelo: `google/antigravity-gemini-3-pro`
   - Modelo: `google/antigravity-gemini-3-flash`
   - Contexto: 1M tokens
   - Suporte a imagem/PDF

4. **Model Studio (Z.ai/Qwen)**
   - Modelos Qwen3 disponiveis como alternativa

### Provedores Desabilitados

- `anthropic` (Claude)
- `openai` (GPT)
- `copilot`

### Mapeamento de Agentes

| Agente | Modelo Principal | Fallback |
|--------|-----------------|----------|
| atlas | opencode/kimi-k2.5-free | - |
| hephaestus | opencode/kimi-k2.5-free | - |
| oracle | zai-coding-plan/glm-4.7 | - |
| prometheus | opencode/kimi-k2.5-free | - |
| sisyphus | zai-coding-plan/glm-4.7 | - |
| metis | zai-coding-plan/glm-4.7 | - |
| momus | opencode/kimi-k2.5-free | - |
| explore | opencode/kimi-k2.5-free | - |
| librarian | zai-coding-plan/glm-4.7 | - |
| multimodal-looker | google/antigravity-gemini-3-flash | - |

### Categorias de Modelo

| Categoria | Modelo | Variante |
|-----------|--------|----------|
| deep | opencode/kimi-k2.5-free | high |
| ultrabrain | opencode/kimi-k2.5-free | high |
| visual-engineering | google/antigravity-gemini-3-pro | high |
| artistry | google/antigravity-gemini-3-pro | high |
| quick | opencode/kimi-k2.5-free | - |
| unspecified-low | zai-coding-plan/glm-4.7 | - |
| unspecified-high | opencode/kimi-k2.5-free | high |
| writing | google/antigravity-gemini-3-flash | - |

### Arquivos Modificados

- `~/.config/opencode/opencode.json` - Provedores e modelos
- `~/.config/opencode/oh-my-opencode.json` - Mapeamento de agentes

### Tools Disponiveis (On-Demand)

Para habilitar tools especificos, use:

```bash
# LSP (Language Server Protocol)
opencode config set tools.lsp.enabled true

# AST-grep
opencode config set tools.astgrep.enabled true

# Tmux
opencode config set tools.tmux.enabled true

# MCP (Model Context Protocol)
opencode config set mcp.enabled true

# Ultrawork (ulw)
opencode config set tools.ultrawork.enabled true
```

### Validacao

```bash
# Verificar sintaxe JSON
python3 -m json.tool ~/.config/opencode/opencode.json > /dev/null && echo "OK"
python3 -m json.tool ~/.config/opencode/oh-my-opencode.json > /dev/null && echo "OK"

# Listar modelos disponiveis
opencode models list
```

## Cadeia de Fallback

1. **Primario**: Kimi 2.5
2. **Secundario**: GLM 4.7
3. **Terciario**: GLM 5
4. **Multimodal**: Gemini 3 Pro/Flash

## Data de Configuracao

2026-02-28 - Configuracao inicial com Kimi 2.5 como modelo principal
