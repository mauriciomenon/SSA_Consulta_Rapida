---
applyTo: '**/*model*.py,**/*ml*.py,**/*ai*.py,**/*embedding*.py,**/*vector*.py'
description: Instrucoes para integracao com HuggingFace e ferramentas de ML
---

# Machine Learning e AI

## Ferramentas MCP Disponiveis

### HuggingFace Hub (`huggingface/hf-mcp-server`)

```
Ferramentas:
- model_search: Buscar modelos por tarefa/nome
- dataset_search: Buscar datasets
- paper_search: Buscar papers academicos
- hub_repo_details: Detalhes de repo especifico
- space_search: Buscar Spaces (demos)
- dynamic_space: Executar tarefas em Spaces
- generate_image: Gerar imagens com Qwen
```

### Chroma (`chroma-core/chroma-mcp`)

```
Banco vetorial para:
- Embeddings de texto
- Busca semantica
- RAG (Retrieval Augmented Generation)
```

## Casos de Uso para SSA

### Busca Semantica de SSAs

```python
# Conceito: usar embeddings para buscar SSAs similares
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('neuralmind/bert-base-portuguese-cased')

def gerar_embedding(texto: str) -> list[float]:
    """Gera embedding para texto de SSA."""
    return model.encode(texto).tolist()

def buscar_similares(query: str, top_k: int = 5):
    """Busca SSAs semanticamente similares."""
    query_embedding = gerar_embedding(query)
    # Usar Chroma para busca
    ...
```

### Classificacao Automatica

```python
# Usar modelo de classificacao para categorizar SSAs
CATEGORIAS = [
    'manutencao_preventiva',
    'manutencao_corretiva',
    'melhoria',
    'seguranca',
]
```

## Busca de Recursos

### Quando usar model_search:

```
- "Preciso de modelo para classificacao de texto em portugues"
- "Qual melhor modelo para NER em portugues?"
- "Modelo para sentiment analysis brasileiro"
```

**Parametros uteis:**
- filter: "language:pt" para modelos em portugues
- sort: "downloads" para mais populares

### Quando usar dataset_search:

```
- "Dataset de texto tecnico em portugues"
- "Dataset para treinar classificador"
```

### Quando usar paper_search:

```
- "Papers sobre BERT em portugues"
- "Pesquisa recente sobre transformers"
```

## Modelos Recomendados para PT-BR

| Tarefa | Modelo |
|--------|--------|
| Embeddings | `neuralmind/bert-base-portuguese-cased` |
| NER | `pierreguillou/bert-base-cased-pt-ner` |
| Classificacao | `neuralmind/bert-large-portuguese-cased` |
| Summarization | `unicamp-dl/ptt5-base-portuguese-vocab` |

## Integracao com Projeto

### Estrutura sugerida

```
core/
├── ml/
│   ├── __init__.py
│   ├── embeddings.py    # Geracao de embeddings
│   ├── classifier.py    # Classificacao de SSAs
│   ├── search.py        # Busca semantica
│   └── models.py        # Configuracao de modelos
```

### Cache de Modelos

```python
import os
from pathlib import Path

# Definir diretorio de cache
CACHE_DIR = Path.home() / '.cache' / 'ssa_models'
os.environ['TRANSFORMERS_CACHE'] = str(CACHE_DIR)
```

## Uso do dynamic_space

Para tarefas rapidas sem instalar dependencias:

```
Tarefas disponiveis:
- image_generation: Gerar imagens
- text_to_speech: Converter texto em audio
- speech_to_text: Transcrever audio
- ocr: Extrair texto de imagens
- background_removal: Remover fundo de imagens
```

**Exemplo:** OCR em documento de SSA escaneado
```
dynamic_space com task="ocr" e imagem do documento
```

## Boas Praticas

1. **Sempre cachear modelos** - Downloads sao lentos
2. **Usar modelos quantizados** quando possivel - Menor memoria
3. **Batch processing** - Processar multiplos textos juntos
4. **GPU opcional** - CPU funciona, apenas mais lento
5. **Fallback** - Sempre ter alternativa se modelo falhar
