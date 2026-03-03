# Manual OhMyOpenCode Multi-Plataforma

## Configuracao Base
Arquivos de config em `~/.config/opencode/`:
- `opencode.json` - Provedores e modelos
- `oh-my-opencode.json` - Mapeamento de agentes
- Path adicional: `~/.bun/bin` e `~/Library/pnpm/global/5/node_modules/.bin`

## OpenCode CLI

### Instalacao
```bash
bun install -g oh-my-opencode@latest
bun install -g @code-yeongyu/comment-checker
```

### Uso Basico
```bash
oh-my-opencode run "tarefa"
oh-my-opencode run --agent Atlas "review codigo"
oh-my-opencode run --agent Hephaestus "refatorar"
oh-my-opencode run --agent Sisyphus "tarefa complexa"
oh-my-opencode run --agent Prometheus "otimizar"
```

### Comandos Magicos
```
/review arquivo.py
/multi-agent Atlas,Hephaestus --task "descricao"
/explain arquivo.py
/test arquivo.py
/secure arquivo.py
/doc arquivo.md
```

### Verificacao
```bash
oh-my-opencode doctor
```

## OpenCode Tauri GUI

### Ativacao do Plugin
1. Abrir Settings (icone engrenagem)
2. Navegar para Plugins
3. Ativar "oh-my-opencode"
4. Reiniciar aplicacao

### Selecao de Agente
- Usar dropdown de modelo no topo da conversa
- Selecionar agente desejado: atlas, sisyphus, hephaestus, prometheus, oracle, explore

### Comandos no Chat
Digitar diretamente no campo de mensagem:
```
/review caminho/arquivo.py
/multi-agent Atlas,Prometheus --task "otimizar cache"
/explain funcao_complexa
```

### Nova Conversa
- Cmd+N (Mac) ou Ctrl+N (Windows/Linux)
- Ou clicar no botao "+" na sidebar

## CCode (Claude Code Router)

### Configuracao
Editar `~/.claude-code-router/config.json`:
```json
{
  "Providers": [
    {
      "name": "opencode-ohmy",
      "type": "openai",
      "api_base_url": "http://localhost:PORTA_OhMyOpenCode",
      "api_key": "sk-dummy"
    }
  ]
}
```

### Uso
```bash
ccode --provider opencode-ohmy
ccode --agent Atlas "tarefa"
```

## KimiCLI

### Instalacao
```bash
npm install -g @kimi-ai/cli
# ou
bun install -g @kimi-ai/cli
```

### Configuracao
```bash
kimi config set api_key SUA_CHAVE
kimi config set model kimi-k2.5
```

### Integracao com OhMyOpenCode
Criar wrapper script `~/.local/bin/kimi-ohmy`:
```bash
#!/bin/bash
oh-my-opencode run --agent Atlas "$@"
```

Tornar executavel:
```bash
chmod +x ~/.local/bin/kimi-ohmy
```

### Uso
```bash
kimi-ohmy "review do codigo"
```

## Agentes Disponiveis

| Agente | Funcao | Modelo | Variante |
|--------|--------|--------|----------|
| Atlas | Visao geral | Kimi K2.5 | high |
| Sisyphus | Tarefas complexas | Kimi K2.5 | high |
| Hephaestus | Engenharia | Kimi K2.5 | high |
| Prometheus | Otimizacao | Kimi K2.5 | high |
| Oracle | Analise profunda | Kimi K2.5 | high |
| Explore | Exploracao | Kimi K2.5 | medium |
| Metis | Planejamento | Kimi K2.5 | high |
| Momus | Fallback | Kimi K2.5 Free | medium |
| Librarian | Documentacao | Kimi K2.5 Free | medium |
| Multimodal-looker | Imagem/PDF | Gemini 3 Flash | - |

## Categorias de Tarefa

| Categoria | Modelo | Uso |
|-----------|--------|-----|
| deep | Kimi K2.5 high | Analise profunda |
| ultrabrain | Kimi K2.5 high | Raciocinio complexo |
| visual-engineering | Gemini 3 Pro high | Diagramas/UI |
| artistry | Gemini 3 Pro high | Design/UX |
| quick | Kimi K2.5 Free low | Tarefas rapidas |
| unspecified-low | GLM 5 low | Fallback simples |
| unspecified-high | Kimi K2.5 high | Fallback complexo |
| writing | Gemini 3 Flash | Texto/documentacao |

## Cadeia de Fallback
1. Kimi K2.5 (assinatura) - Primario
2. Kimi K2.5 Free - Fallback 1
3. GLM 5 - Fallback 2
4. Gemini 3 Pro/Flash - Multimodal

## Exemplos Praticos

### Review de Codigo
```bash
oh-my-opencode run "/review gui/workers/data_loader_worker.py"
```

### Multi-Agente Paralelo
```bash
oh-my-opencode run "/multi-agent Atlas,Prometheus,Sisyphus --task 'refatorar filtros'"
```

### Explicacao
```bash
oh-my-opencode run "/explain core/app_logic.py"
```

### Gerar Testes
```bash
oh-my-opencode run "/test tests/test_workers.py"
```

### Seguranca
```bash
oh-my-opencode run "/secure armazenamento/database_optimized.py"
```

### Documentacao
```bash
oh-my-opencode run "/doc docs/API.md"
```

## Troubleshooting

### Modelo nao encontrado
Verificar `~/.config/opencode/opencode.json`:
```bash
cat ~/.config/opencode/opencode.json | grep -A5 "kimi"
```

### Plugin nao carrega
Reinstalar:
```bash
bun install -g oh-my-opencode@latest
```

### Agente nao responde
Verificar configuracao:
```bash
oh-my-opencode doctor
```

### PATH incorreto
Adicionar ao `~/.zshrc`:
```bash
export PATH="$HOME/.bun/bin:$PATH"
export PATH="$HOME/Library/pnpm/global/5/node_modules/.bin:$PATH"
```

## Atalhos de Teclado

### OpenCode Tauri
- Cmd+N: Nova conversa
- Cmd+Shift+N: Nova janela
- Cmd+Shift+K: Limpar conversa
- Cmd+Enter: Enviar mensagem
- Esc: Cancelar geracao

### CLI
- Ctrl+C: Cancelar execucao
- Ctrl+D: Sair

## Variaveis de Ambiente

```bash
export OPENCODE_DEFAULT_AGENT=Atlas
export OPENCODE_API_KEY=sua_chave
export OHMYOPENCODE_DEBUG=1
```

## Comandos Avancados

### Resumir sessao
```bash
oh-my-opencode run --session-id ses_abc123 "Continue o trabalho"
```

### Output JSON
```bash
oh-my-opencode run --json "tarefa" | jq .sessionId
```

### Comando pos-conclusao
```bash
oh-my-opencode run --on-complete "notify-send 'Pronto'" "tarefa"
```

### Anexar a servidor existente
```bash
oh-my-opencode run --attach http://127.0.0.1:4321 "tarefa"
```

## Limitacoes

- Contexto Kimi K2.5: 1M tokens
- Output maximo: 8K tokens
- Timeout padrao: 300s
- Maximo de agentes em /multi-agent: 5

## Provedores Desabilitados
- anthropic (Claude)
- openai (GPT)
- copilot

## Ferramentas Opcionais
- AST-Grep: Instalado via brew
- Comment-checker: Instalado via pnpm
- LSP: Habilitar sob demanda
- MCP: Habilitar sob demanda
