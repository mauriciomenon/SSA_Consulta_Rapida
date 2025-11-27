---
applyTo: '**/docs/**,**/*.md,**/*doc*.py,**/README*'
description: Instrucoes para documentacao com Markitdown e DeepWiki
---

# Documentacao

## Ferramentas MCP Disponiveis

### Markitdown (`microsoft/markitdown`)

```
Converte para Markdown:
- PDF → MD
- DOCX → MD
- PPTX → MD
- HTML → MD
- Imagens (com OCR) → MD
```

**Quando usar:**
- Converter documentacao legada
- Extrair texto de PDFs tecnicos
- Processar documentos de requisitos

### DeepWiki (`cognitionai/deepwiki`)

```
Documentacao de repositorios GitHub:
- Perguntas sobre projetos externos
- Entender APIs de bibliotecas
- Como usar frameworks
```

**Quando usar:**
- "Como usar feature X da biblioteca Y?"
- "Qual padrao o projeto Z usa para ABC?"
- Documentacao nao disponivel localmente

## Estrutura de Documentacao

```
docs/
├── README.md                    # Visao geral
├── CONTRIBUTING.md              # Guia de contribuicao
├── CHANGELOG.md                 # Historico de mudancas
├── api/                         # Documentacao de API
│   ├── core.md
│   ├── gui.md
│   └── database.md
├── guides/                      # Guias de uso
│   ├── instalacao.md
│   ├── configuracao.md
│   └── uso_basico.md
└── dev/                         # Docs de desenvolvimento
    ├── arquitetura.md
    ├── padroes.md
    └── testes.md
```

## Padroes de Documentacao

### Docstrings (Google Style)

```python
def processar_ssa(
    numero: str,
    incluir_historico: bool = False
) -> dict[str, Any]:
    """
    Processa uma SSA e retorna seus dados.

    Args:
        numero: Numero da SSA no formato XXXX-XXXX
        incluir_historico: Se True, inclui historico de alteracoes

    Returns:
        Dicionario com dados da SSA:
        - numero: Numero formatado
        - descricao: Descricao completa
        - situacao: Status atual

    Raises:
        SSANotFoundError: Se SSA nao existir
        InvalidFormatError: Se numero invalido

    Example:
        >>> processar_ssa("1234-5678")
        {'numero': '1234-5678', 'descricao': '...', ...}
    """
```

### README de Modulo

```markdown
# Nome do Modulo

Breve descricao do proposito.

## Instalacao

```bash
pip install -r requirements.txt
```

## Uso Rapido

```python
from modulo import funcao
resultado = funcao(parametro)
```

## API

### `funcao(param: tipo) -> retorno`

Descricao da funcao.

## Exemplos

Ver pasta `examples/` para mais exemplos.
```

## Conversao de Documentos

### PDF para Markdown

Quando receber documentos PDF:

```
1. Usar Markitdown para converter
2. Revisar formatacao
3. Extrair secoes relevantes
4. Integrar na documentacao do projeto
```

### Documentos Legados

```
1. Identificar formato (DOCX, PDF, HTML)
2. Converter com Markitdown
3. Limpar formatacao
4. Organizar em estrutura padrao
5. Versionar no Git
```

## Consulta de Documentacao Externa

### Bibliotecas usadas no projeto

| Biblioteca | Como consultar |
|------------|----------------|
| PyQt6 | DeepWiki: `riverbank-computing/pyqt6` |
| pandas | DeepWiki: `pandas-dev/pandas` |
| openpyxl | DeepWiki: `theorchard/openpyxl` |
| SQLite | Firecrawl: sqlite.org |

### Exemplo de uso DeepWiki

```
Usuario: "Como fazer drag and drop no PyQt6?"

Acao: Usar DeepWiki para consultar repo do PyQt6
Resultado: Codigo e explicacao da feature
```

## Changelog

### Formato (Keep a Changelog)

```markdown
## [1.2.0] - 2025-11-27

### Added
- Nova funcionalidade de filtro por data

### Changed
- Melhorado desempenho de busca

### Fixed
- Corrigido erro de encoding em CSV

### Security
- Atualizado dependencia com CVE
```

## Integracao com MCPs

### Apos criar documentacao:

```
1. codacy_cli_analyze em arquivos .md (lint)
2. Verificar links quebrados
3. Validar exemplos de codigo
```

### Para documentar codigo:

```
1. Gerar docstrings com padrao Google
2. Extrair API com sphinx/mkdocs
3. Incluir exemplos executaveis
```
