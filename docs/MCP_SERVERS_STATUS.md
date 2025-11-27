# Status dos MCP Servers

**Data:** 2025-11-26
**Ambiente:** WSL Debian Trixie + Windows 11

## Resumo Executivo

- **Docker Engine:** 29.0.4 (ultima versao oficial, instalado e funcional)
- **Docker Compose:** v2.40.3 (plugin instalado corretamente)
- **Python WSL Global:** 3.13.5
- **Python WSL ~/git/.venv:** 3.12.10
- **uv:** 0.9.13 (instalado em ~/.local/bin)
- **Dependencias Chroma:** Corretas (sem conflitos)

## MCP Servers Disponiveis

### 1. Chroma MCP (chromadb)
- **Pacote:** chroma-mcp 0.2.6
- **Backend:** chromadb 1.3.5
- **Status:** ✅ Instalado e funcional
- **Localizacao:** `/home/menon/git/.venv/lib/python3.12/site-packages/chroma_mcp/`
- **Dependencias:** Resolvidas sem conflitos
- **Funcoes principais:**
  - `chroma_create_collection`: Criar colecoes com embeddings
  - `chroma_add_documents`: Adicionar documentos a colecoes
  - `chroma_delete_collection`: Remover colecoes
  - `chroma_delete_documents`: Remover documentos
  - `chroma_query`: Consultar documentos por similaridade

### 2. Docker MCP
- **Status:** ✅ Pronto para uso
- **Docker Engine:** 29.0.4
- **Docker Compose:** v2.40.3 (plugin)
- **Daemon:** Em execucao (PID verificado anteriormente)
- **Ferramentas disponiveis:**
  - Gerenciamento de containers
  - Gerenciamento de imagens
  - Gerenciamento de volumes
  - Compose workflows

### 3. GitHub MCP
- **Status:** ✅ Configurado
- **Funcoes:**
  - Gerenciamento de repositorios
  - Issues e Pull Requests
  - Actions e Workflows
  - Code Search

### 4. Codacy MCP
- **Status:** ✅ Configurado
- **CLI Version:** 7.10.0
- **Java:** OpenJDK 21
- **Localizacao CLI:** `/usr/local/bin/codacy-analysis-cli`
- **JAR:** `/usr/local/lib/codacy-analysis-cli.jar`

### 5. Snyk MCP
- **Status:** ✅ Configurado
- **Regras:** Configuradas em `.github/instructions/snyk_rules.instructions.md`
- **Scan automatico:** Ativo para novos codigos e dependencias

## Configuracao de Ambiente

### WSL PATH
```bash
export PATH="$HOME/.local/bin:$PATH"
```

### Python Virtual Environment
```bash
cd ~/git
source .venv/bin/activate
```

### Docker
```bash
# Verificar status
docker ps
docker compose version

# Usar docker compose (com espaco, nao hifen)
docker compose up -d
docker compose down
```

### UV/UVX
```bash
# Executar com caminho completo ate bashrc ser recarregado
$HOME/.local/bin/uvx <package>

# Apos novo shell
uvx <package>
```

## Problemas Resolvidos

1. ✅ **Docker Engine:** Ja estava na versao mais recente (29.0.4)
2. ✅ **Docker Compose:** Conflito de pacotes resolvido (removido docker-compose antigo, instalado plugin)
3. ✅ **Dependencias Chroma:** Verificadas sem conflitos (`pip check` passou)
4. ✅ **UV:** Instalado no WSL (0.9.13) e adicionado ao PATH
5. ✅ **Codacy CLI:** Funcional no WSL com Java 21

## Proximos Passos Recomendados

1. **Testar MCP Servers via VS Code:**
   - Verificar se GitHub Copilot reconhece todos os servidores MCP
   - Testar comandos do Chroma MCP
   - Testar integracao Docker MCP

2. **Criar compose.yml para Chroma (opcional):**
   - Se precisar de servico ChromaDB separado do MCP
   - Configurar persistencia de dados

3. **Documentar workflows:**
   - Como usar cada MCP server
   - Exemplos de comandos comuns
   - Integracao com CI/CD

## Comandos de Verificacao

```bash
# WSL - Verificar todas as instalacoes
wsl bash -c 'docker --version && docker compose version && uv --version && python3 --version'

# WSL - Verificar ambiente Python
wsl bash -c 'cd ~/git && source .venv/bin/activate && pip check && pip list | grep -i chroma'

# WSL - Verificar Codacy
wsl bash -c 'codacy-analysis-cli --version'

# Windows - Verificar uv
scoop info uv
```

## Notas Importantes

- **ASCII-only policy:** Todo codigo deve usar apenas caracteres ASCII (sem emojis, acentos, cedilhas)
- **Docker Compose:** Usar `docker compose` (com espaco), nao `docker-compose` (com hifen)
- **Java:** OpenJDK 21 instalado para Codacy CLI (Temurin preferido mas nao obrigatorio)
- **CI/CD:** Workflows configurados apenas para branch `main`
