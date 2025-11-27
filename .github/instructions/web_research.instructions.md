---
applyTo: '**'
description: Instrucoes para pesquisa web e acesso a informacoes externas
---

# Pesquisa Web e Informacoes Externas

## PRINCIPIO

**Voce TEM acesso a internet atraves de ferramentas MCP.**

Antes de dizer "nao tenho acesso a internet" ou "nao posso acessar URLs", USE estas ferramentas:

## Ferramentas de Acesso Web

### 1. Firecrawl (Preferido para URLs simples)

```
firecrawl_scrape - Extrair conteudo de uma URL
firecrawl_crawl - Crawl de multiplas paginas
firecrawl_search - Busca web
firecrawl_extract - Extrair dados estruturados com schema
```

**Exemplos de uso:**
- "O que diz o site X sobre Y?" → `firecrawl_scrape` na URL
- "Busque informacoes sobre Z" → `firecrawl_search`
- "Extraia todos os links de W" → `firecrawl_map`

### 2. Apify (Para scraping complexo)

```
search-actors - Encontrar scrapers especializados
call-actor - Executar um scraper
```

**Usar quando:**
- Sites com JavaScript pesado
- Login necessario
- Paginacao complexa
- Rate limiting

### 3. Playwright (Para interacao com browser)

```
browser_navigate - Abrir URL
browser_click - Clicar em elementos
browser_type - Preencher formularios
browser_screenshot - Capturar tela
```

**Usar quando:**
- Precisa interagir com a pagina
- Sites Single Page Application (SPA)
- Precisa de screenshots

### 4. DeepWiki (Para repos GitHub)

```
Perguntas sobre repositorios GitHub externos
```

**Usar quando:**
- Usuario pergunta sobre biblioteca/framework
- Documentacao de projeto open source
- Como usar uma API de repo externo

### 5. HuggingFace (Para ML/AI)

```
model_search - Buscar modelos
dataset_search - Buscar datasets
paper_search - Buscar papers academicos
```

**Usar quando:**
- Tarefas de machine learning
- Buscar papers cientificos
- Encontrar datasets

## Fluxo de Decisao

```
Usuario pede informacao externa
          |
          v
    E sobre repo GitHub?
      /          \
    Sim          Nao
     |            |
     v            v
  DeepWiki    E sobre ML/AI?
                /      \
              Sim      Nao
               |        |
               v        v
          HuggingFace  URL especifica?
                         /      \
                       Sim      Nao
                        |        |
                        v        v
                   Firecrawl  Firecrawl
                   _scrape    _search
```

## Exemplos Praticos

### "Me fale sobre a biblioteca pandas"
1. Usar DeepWiki para o repo pandas-dev/pandas
2. Ou firecrawl_scrape em pandas.pydata.org

### "Qual a ultima versao do React?"
1. firecrawl_scrape em reactjs.org ou npmjs.com/package/react
2. Ou getLatestComponentVersion do Sonatype

### "Busque papers sobre transformers"
1. paper_search do HuggingFace
2. Retornar links e resumos

### "O que tem nesse site: https://example.com"
1. firecrawl_scrape na URL
2. Retornar conteudo extraido

## NUNCA DIGA

- "Nao tenho acesso a internet"
- "Nao posso acessar URLs"
- "Meu conhecimento e limitado a..."
- "Nao consigo verificar informacoes atuais"

**SEMPRE tente usar uma ferramenta primeiro.**
