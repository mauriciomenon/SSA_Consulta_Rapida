---
applyTo: '**/extracao/**,**/*excel*.py,**/*csv*.py,**/*extract*.py,**/*import*.py'
description: Instrucoes para extracao de dados Excel/CSV com ferramentas MCP
---

# Extracao de Dados - Excel/CSV

## Estrutura do Modulo

```
extracao/
├── __init__.py
├── leitor_excel.py      # Leitura de arquivos Excel
├── leitor_csv.py        # Leitura de arquivos CSV
├── validador.py         # Validacao de dados
└── transformador.py     # Transformacao de dados
```

## Padroes de Leitura

### Excel com openpyxl/pandas

```python
from typing import Generator
import pandas as pd

def ler_excel_em_chunks(
    caminho: str,
    tamanho_chunk: int = 1000
) -> Generator[pd.DataFrame, None, None]:
    """
    Le arquivo Excel em chunks para economia de memoria.

    Args:
        caminho: Caminho do arquivo Excel
        tamanho_chunk: Numero de linhas por chunk

    Yields:
        DataFrame com chunk de dados
    """
    for chunk in pd.read_excel(caminho, chunksize=tamanho_chunk):
        yield chunk
```

### CSV com encoding brasileiro

```python
ENCODINGS_BRASIL = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']

def detectar_encoding(caminho: str) -> str:
    """Detecta encoding do arquivo tentando varios."""
    for enc in ENCODINGS_BRASIL:
        try:
            with open(caminho, 'r', encoding=enc) as f:
                f.read(1024)
            return enc
        except UnicodeDecodeError:
            continue
    return 'utf-8'  # fallback
```

## Validacao de Dados

### Schema de SSA

```python
CAMPOS_OBRIGATORIOS = [
    'numero_ssa',
    'descricao',
    'situacao',
    'responsavel',
]

CAMPOS_DATA = [
    'data_emissao',
    'data_programada',
    'data_conclusao',
]

def validar_ssa(dados: dict) -> tuple[bool, list[str]]:
    """Valida dados de SSA retornando (valido, erros)."""
    erros = []
    for campo in CAMPOS_OBRIGATORIOS:
        if not dados.get(campo):
            erros.append(f"Campo obrigatorio ausente: {campo}")
    return len(erros) == 0, erros
```

## Integracao com MCPs

### Dados de Fontes Web

Quando precisar extrair dados de fontes web (APIs, sites):

```
1. URL conhecida → firecrawl_scrape
2. Dados estruturados → firecrawl_extract com schema
3. Site dinamico → Apify ou Playwright
```

**Exemplo de schema para extracao:**
```json
{
  "type": "object",
  "properties": {
    "numero_ssa": {"type": "string"},
    "descricao": {"type": "string"},
    "situacao": {"type": "string"}
  }
}
```

### Verificacao de Qualidade

Apos importacao de dados:

```
1. codacy_cli_analyze nos scripts de extracao
2. Validar schema dos dados importados
3. Verificar duplicatas no banco
```

## Tratamento de Erros

```python
class ExtractionError(Exception):
    """Erro base de extracao."""
    pass

class FileNotFoundError(ExtractionError):
    """Arquivo nao encontrado."""
    pass

class InvalidDataError(ExtractionError):
    """Dados invalidos no arquivo."""
    pass

class EncodingError(ExtractionError):
    """Erro de encoding do arquivo."""
    pass
```

## Logging de Extracao

```python
import logging

logger = logging.getLogger('extracao')

def log_extracao(arquivo: str, registros: int, erros: int):
    """Loga resultado de extracao."""
    logger.info(
        f"Extracao concluida: {arquivo} | "
        f"Registros: {registros} | Erros: {erros}"
    )
```

## Fluxo Completo

```
1. Detectar encoding do arquivo
2. Ler em chunks (se grande)
3. Validar cada registro
4. Transformar para formato interno
5. Inserir no banco (upsert)
6. Logar resultado
7. Reportar erros se houver
```
