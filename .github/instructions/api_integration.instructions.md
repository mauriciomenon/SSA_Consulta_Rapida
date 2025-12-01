---
applyTo: '**/*api*.py,**/*client*.py,**/*request*.py,**/*http*.py,**/*service*.py'
description: Instrucoes para integracao com APIs externas usando Playwright e Firecrawl
---

# Integracao com APIs Externas

## Ferramentas MCP Disponiveis

### Firecrawl (`firecrawl/firecrawl-mcp-server`)

```
Para APIs e sites:
- firecrawl_scrape: Extrair conteudo de URL
- firecrawl_extract: Extrair dados estruturados
- firecrawl_search: Buscar na web
- firecrawl_map: Mapear URLs de site
```

### Playwright (`microsoft/playwright-mcp`)

```
Para automacao de browser:
- browser_navigate: Abrir URL
- browser_click: Clicar em elementos
- browser_type: Preencher campos
- browser_screenshot: Capturar tela
- browser_snapshot: Snapshot acessibilidade
```

### Apify (`com.apify/apify-mcp-server`)

```
Para scraping avancado:
- search-actors: Buscar scrapers
- call-actor: Executar scraper
```

## Padroes de Integracao

### Cliente HTTP Base

```python
from typing import Any
import httpx
from dataclasses import dataclass

@dataclass
class APIConfig:
    """Configuracao de API externa."""
    base_url: str
    timeout: int = 30
    headers: dict[str, str] | None = None

class APIClient:
    """Cliente base para APIs externas."""

    def __init__(self, config: APIConfig):
        self.config = config
        self._client = httpx.Client(
            base_url=config.base_url,
            timeout=config.timeout,
            headers=config.headers or {},
        )

    def get(self, endpoint: str, **params) -> dict[str, Any]:
        """GET request com tratamento de erros."""
        response = self._client.get(endpoint, params=params)
        response.raise_for_status()
        return response.json()

    def post(self, endpoint: str, data: dict) -> dict[str, Any]:
        """POST request com tratamento de erros."""
        response = self._client.post(endpoint, json=data)
        response.raise_for_status()
        return response.json()

    def close(self):
        """Fecha cliente."""
        self._client.close()
```

### Retry com Backoff

```python
import time
from functools import wraps

def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
):
    """Decorator para retry com exponential backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = base_delay
            last_exception = None

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        time.sleep(min(delay, max_delay))
                        delay *= 2

            raise last_exception
        return wrapper
    return decorator
```

## Extracao de Dados Web

### Com Firecrawl

```
Cenario: Extrair dados de site sem API

1. Identificar URL alvo
2. firecrawl_scrape para conteudo bruto
3. firecrawl_extract com schema para estruturar
```

**Schema de extracao:**
```json
{
  "type": "object",
  "properties": {
    "titulo": {"type": "string"},
    "data": {"type": "string"},
    "conteudo": {"type": "string"}
  },
  "required": ["titulo"]
}
```

### Com Playwright

```
Cenario: Site com JavaScript/login

1. browser_navigate para URL
2. browser_type para preencher login
3. browser_click para submeter
4. browser_snapshot para extrair dados
```

### Com Apify

```
Cenario: Scraping complexo/em escala

1. search-actors para encontrar scraper
2. fetch-actor-details para ver inputs
3. call-actor para executar
```

## Tratamento de Erros

```python
class APIError(Exception):
    """Erro base de API."""
    pass

class RateLimitError(APIError):
    """Rate limit excedido."""
    def __init__(self, retry_after: int = 60):
        self.retry_after = retry_after
        super().__init__(f"Rate limit. Retry after {retry_after}s")

class AuthenticationError(APIError):
    """Erro de autenticacao."""
    pass

class NotFoundError(APIError):
    """Recurso nao encontrado."""
    pass
```

## Cache de Respostas

```python
from functools import lru_cache
from datetime import datetime, timedelta

class CachedAPIClient(APIClient):
    """Cliente com cache de respostas."""

    def __init__(self, config: APIConfig, cache_ttl: int = 300):
        super().__init__(config)
        self.cache_ttl = cache_ttl
        self._cache: dict[str, tuple[Any, datetime]] = {}

    def get_cached(self, endpoint: str, **params) -> dict[str, Any]:
        """GET com cache."""
        cache_key = f"{endpoint}:{params}"

        if cache_key in self._cache:
            data, timestamp = self._cache[cache_key]
            if datetime.now() - timestamp < timedelta(seconds=self.cache_ttl):
                return data

        data = self.get(endpoint, **params)
        self._cache[cache_key] = (data, datetime.now())
        return data
```

## Seguranca

### Credenciais

```python
import os
from pathlib import Path

def get_api_key(service: str) -> str:
    """Obtem API key de variavel de ambiente."""
    key = os.environ.get(f"{service.upper()}_API_KEY")
    if not key:
        raise ValueError(f"API key para {service} nao configurada")
    return key
```

### Validacao de URLs

```python
from urllib.parse import urlparse

ALLOWED_HOSTS = ['api.exemplo.com', 'dados.gov.br']

def validar_url(url: str) -> bool:
    """Valida se URL e permitida."""
    parsed = urlparse(url)
    return parsed.hostname in ALLOWED_HOSTS
```

## Fluxo de Integracao

```
1. Identificar fonte de dados
2. Verificar se tem API oficial
3. Se nao, usar Firecrawl/Playwright
4. Implementar cliente com retry
5. Adicionar cache se apropriado
6. Tratar erros especificos
7. Logar requisicoes
8. codacy_cli_analyze no codigo
```
