---
applyTo: '**'
description: Instrucoes para uso proativo de ferramentas MCP em todas as tarefas
---

# Ferramentas MCP - Guia de Uso Proativo

## PRINCIPIO FUNDAMENTAL

**NUNCA diga que nao pode fazer algo sem antes verificar se ha uma ferramenta MCP disponivel.**

---

## Categoria 1: Seguranca e Qualidade (SEMPRE USAR)

### Codacy (`codacy/codacy-mcp-server`)
**OBRIGATORIO apos qualquer edicao de arquivo**

```
Ferramentas:
- codacy_cli_analyze: Analise local de codigo
- codacy_get_repository_issues: Issues do repo
- codacy_get_file_issues: Issues de arquivo especifico
```

**Regra**: Apos editar arquivo → executar `codacy_cli_analyze` → corrigir issues encontrados

### Snyk (`snyk/snyk-mcp-server`)
**Para seguranca de codigo e dependencias**

```
Ferramentas:
- snyk_code_scan: SAST - analise estatica de seguranca
- snyk_test: Vulnerabilidades em dependencias
- snyk_container_scan: Scan de imagens Docker
- snyk_iac_scan: Scan de Infrastructure as Code
```

**Usar quando**: Adicionar dependencias, editar codigo sensivel, antes de commits importantes

### SonarQube (`sonarqube`)
**Para code smells, bugs, debt tecnica**

```
Ferramentas:
- sonarqube_analyze_file: Analise de arquivo
- sonarqube_list_potential_security_issues: Hotspots de seguranca
```

### Sonatype (`com.sonatype/dependency-management-mcp-server`)
**Para gerenciamento de dependencias**

```
Ferramentas:
- getComponentVersion: Info sobre versao de dependencia
- getLatestComponentVersion: Ultima versao disponivel
- getRecommendedComponentVersions: Versoes recomendadas por score
```

**Usar quando**: Adicionar/atualizar dependencias, verificar CVEs

---

## Categoria 2: Git e Versionamento

### GitKraken (`gitkraken/gitkraken-mcp-server`)
**Para todas operacoes git**

```
Ferramentas:
- git_add_or_commit: Stage e commit de arquivos
- git_log: Historico de commits
- git_diff: Diferencas entre commits
- git_branch: Listar/criar branches
- git_switch: Trocar de branch
- git_create_pull_request: Criar PR
- git_get_pull_request_comments: Comentarios de PR
```

**Preferir sobre comandos git manuais** para melhor integracao

### GitHub MCP (`github/github-mcp-server`)
**Para API GitHub avancada**

```
Acesso a: repos, issues, PRs, actions, releases
```

### Sentry (`getsentry/sentry-mcp`)
**Para monitoramento de erros**

```
Rastreamento de exceptions e crashes em producao
```

---

## Categoria 3: Pesquisa e Web

### Firecrawl (`firecrawl/firecrawl-mcp-server`)
**Para extrair conteudo da web**

```
Ferramentas:
- firecrawl_scrape: Extrair conteudo de URL unica
- firecrawl_crawl: Crawl de site completo
- firecrawl_map: Mapear URLs de um site
- firecrawl_search: Busca web
- firecrawl_extract: Extrair dados estruturados
```

**Usar quando**: Usuario pede info de site, documentacao externa, dados publicos

### Apify (`com.apify/apify-mcp-server`)
**Para scraping avancado**

```
Ferramentas:
- search-actors: Buscar scrapers pre-construidos
- fetch-actor-details: Detalhes de um actor
- call-actor: Executar um actor
```

**Usar quando**: Sites dinamicos, scraping complexo, automacao web

### Playwright (`microsoft/playwright-mcp`)
**Para automacao de browser**

```
Ferramentas:
- browser_navigate: Navegar para URL
- browser_click: Clicar em elemento
- browser_type: Digitar texto
- browser_screenshot: Capturar tela
- browser_snapshot: Snapshot de acessibilidade
```

**Usar quando**: Testes E2E, interacao com sites, capturas de tela

### DeepWiki (`cognitionai/deepwiki`)
**Para documentacao de repos externos**

```
Perguntas sobre repositorios GitHub que nao estao no workspace
```

**Usar quando**: Usuario pergunta sobre projeto open source, biblioteca externa

---

## Categoria 4: Machine Learning e Dados

### HuggingFace (`huggingface/hf-mcp-server`)
**Para recursos de ML**

```
Ferramentas:
- model_search: Buscar modelos
- dataset_search: Buscar datasets
- paper_search: Buscar papers
- hub_repo_details: Detalhes de repo HF
- space_search: Buscar Spaces
- dynamic_space: Usar Spaces (image gen, TTS, OCR)
- generate_image: Gerar imagens com Qwen
```

**Usar quando**: Tarefas de ML, buscar modelos, datasets, papers academicos

### Chroma (`chroma-core/chroma-mcp`)
**Para banco vetorial**

```
Operacoes com embeddings, busca semantica, RAG
```

### Elasticsearch (`elastic/mcp-server-elasticsearch`)
**Para busca full-text**

```
Queries em clusters Elasticsearch
```

---

## Categoria 5: Design e Documentacao

### Figma (`com.figma.mcp/mcp`)
**Para designs**

```
Ferramentas:
- generate_code: Gerar codigo de node Figma
- get_code_connect_map: Mapeamento de componentes
- get_node_metadata: Metadados de node
```

**Usar quando**: Implementar UI de design, extrair assets

### Markitdown (`microsoft/markitdown`)
**Para conversao de documentos**

```
Converter PDF, DOCX, HTML, imagens para Markdown
```

---

## Categoria 6: Infraestrutura

### Serena (`oraios/serena`)
**Para navegacao e refatoracao de codigo**

```
Ferramentas:
- find_symbol: Encontrar simbolos no codigo
- find_referencing_symbols: Referencias a simbolo
- get_symbols_overview: Overview de arquivo
- rename_symbol: Renomear simbolo
- replace_symbol_body: Substituir corpo de funcao
- insert_before/after_symbol: Inserir codigo
```

**Usar quando**: Refatoracao, navegacao em codebase grande

### Supabase (`com.supabase/mcp`)
**Para banco Supabase**

```
Queries SQL, migrations, operacoes de banco
```

### GoReleaser (`io.github.goreleaser/mcp`)
**Para releases**

```
Build e release automatizado de binarios
```

---

## Fluxo de Trabalho Recomendado

### Ao editar codigo:
1. Fazer a edicao
2. `codacy_cli_analyze` no arquivo
3. Corrigir issues
4. Se mudou seguranca: `snyk_code_scan`

### Ao adicionar dependencia:
1. Adicionar ao requirements/package.json
2. `getRecommendedComponentVersions` para verificar
3. `snyk_test` para CVEs

### Ao responder pergunta sobre site/repo externo:
1. Verificar se Firecrawl/DeepWiki pode ajudar
2. Usar a ferramenta apropriada
3. Responder com dados reais

### Ao fazer operacoes git:
1. Preferir GitKraken sobre comandos manuais
2. Usar `git_add_or_commit` para commits
3. Usar `git_log` para historico
