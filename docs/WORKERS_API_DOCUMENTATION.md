# Documentação Técnica - Workers Assíncronos da GUI

## Visão Geral

## Atualizacao 2026-03-27

- `RescanWorker` tambem sustenta o fluxo de importacao explicita disparado pela GUI.
- O sync manual de derivadas agora roda fora do thread principal em runtime normal, com entrega do resultado de volta para a GUI.
- O estado de fila/execucao passou a ser mais explicito no contrato da GUI para evitar falso sinal de `db_updated` imediato.
- A validacao de `load_other_database()` agora segue o mesmo principio: trabalho de I/O fora do thread principal e entrega posterior na GUI.

Este documento descreve a arquitetura, interfaces e APIs dos workers assíncronos utilizados na interface gráfica do sistema SSA Consulta Rápida.

## Índice

1. [Arquitetura de Workers](#arquitetura-de-workers)
2. [DataLoaderWorker](#dataloaderworker)
3. [FilterWorker](#filterworker)
4. [Padrões de Uso](#padrões-de-uso)
5. [Sinais e Slots](#sinais-e-slots)
6. [Tratamento de Erros](#tratamento-de-erros)
7. [Testes](#testes)

---

## Arquitetura de Workers

### Visão Geral da Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│                    SSAMainWindow (QMainWindow)                   │
│                          │                                       │
│           ┌──────────────┼──────────────┐                       │
│           │              │              │                       │
│           ▼              ▼              ▼                       │
│    ┌────────────┐ ┌────────────┐ ┌────────────┐                │
│    │DataLoader  │ │  Filter    │ │  Rescan    │                │
│    │  Worker    │ │  Worker    │ │  Worker    │                │
│    └─────┬──────┘ └─────┬──────┘ └─────┬──────┘                │
│          │              │              │                       │
│          ▼              ▼              ▼                       │
│    ┌────────────┐ ┌────────────┐ ┌────────────┐                │
│    │  SQLite    │ │   Cache    │ │   Excel    │                │
│    │   DB       │ │   LRU      │ │  Files     │                │
│    └────────────┘ └────────────┘ └────────────┘                │
└─────────────────────────────────────────────────────────────────┘
```

### Princípios de Design

1. **Assíncrono por Padrão**: Todas as operações de I/O são executadas em threads separadas
2. **Cancelável**: Todos os workers suportam cancelamento seguro via `requestInterruption()`
3. **Cache Inteligente**: Resultados são cacheados quando apropriado
4. **Signal-Based**: Comunicação via PyQt Signals para thread-safety
5. **Fail-Safe**: Tratamento robusto de erros sem crashar a UI

---

## DataLoaderWorker

### Descrição

Worker responsável por carregar dados do banco SQLite de forma assíncrona, com suporte a paginação e ordenação segura.

### Localização

`gui/workers/data_loader_worker.py`

### Classe: `DataLoaderWorker`

Herda de: `PyQt6.QtCore.QThread`

#### Sinais

| Sinal | Tipo | Descrição |
|-------|------|-----------|
| `data_loaded` | `pyqtSignal(pd.DataFrame)` | Emitido quando dados são carregados com sucesso |
| `error_occurred` | `pyqtSignal(str)` | Emitido quando ocorre um erro durante o carregamento |

#### Atributos de Classe

| Atributo | Tipo | Descrição |
|----------|------|-----------|
| `_ALLOWED_ORDER_COLUMNS` | `set[str]` | Whitelist de colunas permitidas em ORDER BY |
| `_IDENTIFIER_RE` | `Pattern` | Regex para validar identificadores SQL |

#### Construtor

```python
def __init__(
    self,
    db_path: str,           # Caminho para o arquivo SQLite
    table_name: str,        # Nome da tabela a ser consultada
    limit: int | None = None,   # Limite de registros (None = sem limite)
    offset: int = 0,        # Offset para paginação
    order_by: str | None = None  # Cláusula ORDER BY
)
```

#### Métodos Públicos

##### `cancel() -> None`

Solicita cancelamento do worker.

```python
worker = DataLoaderWorker("ssas.db", "ssa_table")
worker.start()
# ... posteriormente
worker.cancel()  # Solicita interrupção segura
```

**Thread-Safe**: Sim
**Bloqueante**: Não

#### Métodos Protegidos

##### `_is_cancelled() -> bool`

Verifica se o worker foi cancelado.

**Retorna**: `True` se cancelado, `False` caso contrário

##### `_sanitize_identifier(value: str) -> str`

Remove caracteres perigosos de identificadores SQL.

**Proteção**: SQL Injection
**Retorna**: String sanitizada ou vazia se inválido

##### `_quote_identifier(value: str) -> str`

Escapa identificadores SQL com aspas.

**Exemplo**: `ssa_table` → `"ssa_table"`

##### `_resolve_target_table() -> str`

Resolve o nome da tabela alvo, com fallback para "ssa_table".

**Lógica**:
1. Verifica se tabela solicitada existe
2. Se não existe, tenta "ssa_table"
3. Retorna fallback se nenhuma existe

##### `_normalize_order_by(order_by: str | None) -> str | None`

Normaliza e valida cláusula ORDER BY.

**Validações**:
- Colunas devem estar na whitelist
- Direção deve ser ASC ou DESC
- Previne SQL injection

**Exceções**:
- `ValueError`: ORDER BY inválido ou coluna não permitida

#### Exemplos de Uso

### Exemplo 1: Carregamento Básico

```python
from gui.workers.data_loader_worker import DataLoaderWorker

# Criar worker
worker = DataLoaderWorker("ssas.db", "ssa_table")

# Conectar signals
worker.data_loaded.connect(on_data_loaded)
worker.error_occurred.connect(on_error)

# Iniciar
worker.start()
```

### Exemplo 2: Paginação

```python
# Carregar página 3 com 50 registros por página
page_size = 50
page_number = 3

worker = DataLoaderWorker(
    "ssas.db",
    "ssa_table",
    limit=page_size,
    offset=(page_number - 1) * page_size,
    order_by="numero_ssa DESC"
)
```

### Exemplo 3: Cancelamento

```python
worker = DataLoaderWorker("ssas.db", "ssa_table")
worker.start()

# Se usuário cancelar operação
if user_cancelled:
    worker.cancel()
    worker.wait(timeout=5000)  # Esperar até 5 segundos
```

---

## FilterWorker

### Descrição

Worker responsável por filtrar DataFrames de forma assíncrona, com cache LRU inteligente.

### Localização

`gui/workers/filter_worker.py`

### Classe: `FilterWorker`

Herda de: `PyQt6.QtCore.QThread`

#### Sinais

| Sinal | Tipo | Descrição |
|-------|------|-----------|
| `filter_finished` | `pyqtSignal(pd.DataFrame)` | Emitido com resultado da filtragem |
| `error_occurred` | `pyqtSignal(str)` | Emitido quando ocorre erro na filtragem |

#### Atributos de Classe

| Atributo | Tipo | Descrição |
|----------|------|-----------|
| `_cache` | `FilterCache` | Cache LRU compartilhado entre instâncias |

#### Construtor

```python
def __init__(
    self,
    df_completo: pd.DataFrame,     # DataFrame a ser filtrado
    search_chunks: list,           # Lista de chunks de busca
    default_mode: str = 'contains',  # Modo de busca padrão
    cache_context: str | None = None  # Contexto adicional para chave de cache
)
```

#### Métodos Públicos

##### `cancel() -> None`

Solicita cancelamento do worker.

```python
worker = FilterWorker(df, [["termo1"], ["termo2"]])
worker.start()
worker.cancel()  # Cancela processamento
```

##### `_build_df_hash(df_completo: pd.DataFrame) -> str`

**Método Estático**

Cria hash estrutural do DataFrame para chave de cache.

**Algoritmo de Amostragem**:
- DataFrames ≤ 24 linhas: Usa DataFrame completo
- DataFrames > 24 linhas: Amostra estratificada (head + mid + tail)

**Retorna**: Hash hexadecimal de 16 caracteres

**Exemplo**:
```python
df = pd.DataFrame({'col': [1, 2, 3]})
hash_val = FilterWorker._build_df_hash(df)
# Retorna: '84e3d1d94822c03e'
```

#### Exemplos de Uso

### Exemplo 1: Filtragem Básica

```python
from gui.workers.filter_worker import FilterWorker

# DataFrame de exemplo
df = pd.DataFrame({
    'numero_ssa': ['SSA-0001', 'SSA-0002', 'SSA-0003'],
    'situacao': ['APV', 'STE', 'APV']
})

# Criar worker com termos de busca
worker = FilterWorker(df, [["APV"]])
worker.filter_finished.connect(on_filter_finished)
worker.error_occurred.connect(on_error)

worker.start()
```

### Exemplo 2: Múltiplos Chunks

```python
# Buscar SSAs que contenham "APV" OU "STE"
worker = FilterWorker(df, [["APV"], ["STE"]])

# Resultado: união dos filtros (OR lógico)
```

### Exemplo 3: Com Cache

```python
# Primeira execução - cache miss
worker1 = FilterWorker(df, [["test"]], cache_context='{"tab":"main"}')
worker1.start()
worker1.wait()

# Segunda execução - cache hit (mesmo df_hash e search_chunks)
worker2 = FilterWorker(df, [["test"]], cache_context='{"tab":"main"}')
worker2.start()  # Usa cache, não reprocessa
```

---

## Padrões de Uso

### Padrão 1: Chain de Workers

```python
def load_and_filter():
    # 1. Carregar dados
    loader = DataLoaderWorker("ssas.db", "ssa_table")
    
    def on_data_loaded(df):
        # 2. Filtrar dados carregados
        filter_worker = FilterWorker(df, [["APV"]])
        filter_worker.filter_finished.connect(on_filtered)
        filter_worker.start()
    
    loader.data_loaded.connect(on_data_loaded)
    loader.start()
```

### Padrão 2: Worker com Timeout

```python
worker = DataLoaderWorker("ssas.db", "ssa_table")
worker.start()

# Esperar com timeout
if not worker.wait(timeout=30000):  # 30 segundos
    worker.cancel()
    logger.warning("Worker timeout, cancelado")
```

### Padrão 3: Worker Pool

```python
# Executar múltiplos workers em paralelo
workers = []
for page in range(5):
    worker = DataLoaderWorker(
        "ssas.db", "ssa_table",
        limit=50, offset=page*50
    )
    workers.append(worker)
    worker.start()

# Aguardar todos
for worker in workers:
    worker.wait()
```

---

## Sinais e Slots

### Boas Práticas

1. **Sempre conectar signals antes de iniciar o worker**
   ```python
   worker.data_loaded.connect(handler)  # Conectar
   worker.start()                        # Depois iniciar
   ```

2. **Usar `QueuedConnection` para thread-safety**
   ```python
   worker.data_loaded.connect(
       handler,
       Qt.ConnectionType.QueuedConnection
   )
   ```

3. **Desconectar signals ao finalizar**
   ```python
   worker.data_loaded.disconnect(handler)
   ```

### Handlers Típicos

```python
def on_data_loaded(df: pd.DataFrame):
    """Handler para dados carregados."""
    if df.empty:
        show_empty_message()
    else:
        update_table(df)
        update_status(f"{len(df)} registros carregados")

def on_error(error_msg: str):
    """Handler para erros."""
    show_error_dialog(error_msg)
    logger.error(f"Worker error: {error_msg}")
```

---

## Tratamento de Erros

### Tipos de Erro

| Erro | Causa | Handler |
|------|-------|---------|
| `sqlite3.Error` | Falha de banco de dados | `error_occurred` emitido |
| `ValueError` | ORDER BY inválido | `error_occurred` emitido |
| `TypeError` | Tipo incorreto retornado | `error_occurred` emitido |
| Cancelamento | Usuário cancelou | Nenhum sinal emitido |

### Estratégia de Retry

```python
def run_with_retry(worker, max_retries=3):
    for attempt in range(max_retries):
        errors = []
        worker.error_occurred.connect(errors.append)
        worker.start()
        worker.wait()
        
        if not errors:
            return True
        
        if attempt < max_retries - 1:
            time.sleep(2 ** attempt)  # Backoff exponencial
    
    return False
```

---

## Testes

### Suite de Testes

Localização: `tests/test_workers_advanced.py`

#### Executar Testes

```bash
# Usando venv do projeto
source .venv/bin/activate
python -m pytest tests/test_workers_advanced.py -v

# Executar apenas testes unitários
python -m pytest tests/test_workers_advanced.py::TestDataLoaderWorkerUnit -v

# Executar testes de performance
python -m pytest tests/test_workers_advanced.py::TestWorkerPerformance -v
```

#### Cobertura de Testes

- **TestDataLoaderWorkerUnit**: 9 testes
  - Sanitização de identificadores
  - Normalização de ORDER BY
  - Resolução de tabela

- **TestDataLoaderWorkerIntegration**: 6 testes
  - Emissão de signals
  - Cancelamento
  - Paginação

- **TestFilterWorkerUnit**: 8 testes
  - Hash de DataFrame
  - Estabilidade do cache

- **TestFilterWorkerIntegration**: 9 testes
  - Filtragem com cache
  - Cancelamento
  - Tratamento de erros

- **TestWorkerPerformance**: 2 testes
  - Performance de cache
  - Performance de hash

- **TestWorkerRegression**: 3 testes
  - SQL injection
  - Caracteres especiais
  - Concorrência

**Total**: 35 testes cobrindo 100% dos métodos públicos

---

## Referências

### Arquivos Relacionados

- `gui/workers/data_loader_worker.py` - Implementação do DataLoaderWorker
- `gui/workers/filter_worker.py` - Implementação do FilterWorker
- `gui/workers/rescan_worker.py` - Implementação do RescanWorker
- `gui/cache/filter_cache.py` - Implementação do cache LRU
- `tests/test_workers_advanced.py` - Suite de testes completa

### Documentação Externa

- [PyQt6 QThread](https://doc.qt.io/qtforpython-6/PyQt6/QtCore/QThread.html)
- [PyQt6 Signals & Slots](https://doc.qt.io/qtforpython-6/overviews/signalsandslots.html)
- [Pandas DataFrame](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.html)

---

## Changelog

### v2.0.0 (2025-02-23)
- Adicionada suite de testes avançada (35 testes)
- Documentação técnica completa das APIs
- Testes de performance e regressão

### v1.0.0 (2025-02-20)
- Implementação inicial dos workers
- Cache LRU para FilterWorker
- Proteção SQL injection no DataLoaderWorker

---

*Documentacao sincronizada com `dev` em 2026-03-27.*

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->

