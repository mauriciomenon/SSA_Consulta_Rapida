# Documentac~ao T?cnica - Workers Ass'incronos da GUI

## Vis~ao Geral

Este documento descreve a arquitetura, interfaces e APIs dos workers ass'incronos utilizados na interface gr'afica do sistema SSA Consulta R'apida.

## 'Indice

1. [Arquitetura de Workers](#arquitetura-de-workers)
2. [DataLoaderWorker](#dataloaderworker)
3. [FilterWorker](#filterworker)
4. [Padr~oes de Uso](#padr~oes-de-uso)
5. [Sinais e Slots](#sinais-e-slots)
6. [Tratamento de Erros](#tratamento-de-erros)
7. [Testes](#testes)

---

## Arquitetura de Workers

### Vis~ao Geral da Arquitetura

```
+-----%%%%%%%%%%%%%%%%%%%%%%%--------%%%%%%%%%%%%%%%%%%%%%%%%---%|%
%                    SSAMainWindow (QMainWindow)                   |
|                          |                                       |
|           %%%-------%+%%%<%%%%%%%%%%%%%--%                      |%
%           |              |              |                       |
|                                                              |
|    %%-------+%%%% %%%%%%%%%%%%%% %%%%----%%%%%%          |     %
%    |DataLoader  | %  Filter  | % %  Rescan    |                |
%    |  Worker    | %  Worker    | |  Worker   |%                |
|   +--+%%%,%%%%%%%% %%%%%%,%%%%--+---%%%%%,%%%%%%%%                |
|      |   %    |         %              |                       |
|                                                             |
|    %%-------+%%%% %%%%%%%%%%%%%% %%%%----%%%%%%          |     %
%    |  SQLite    | %   Cache  | % |   Excel    |               |%
|    |   DB      |% %   LRU      | |  Files   | %                |
|  +-+-%%%%%%%%%%%% %%%%%%%%%---+--%%%%%%%%%%%%%%                |
+---%%%%%%%%%%%%%%%%%%%%%%--------%%%%%%%%%%%%%%%%%%%%%%%%----%%%%%
```

###'iPrinc?pios de Design

1. **Ass'incrono por Padr~ao**: Todas as operac?es de I/O s~ao executadas em threads separadas
2. **Cancel'avel**: Todos os workers suportam cancelamento seguro via `requestInterruption()`
3. **Cache Inteligente**: Resultados s~ao cacheados quando apropriado
4. **Signal-Based**: Comunicac~ao via PyQt Signals para thread-safety
5. **Fail-Safe**: Tratamento robusto de erros sem crashar a UI

---

## DataLoaderWorker

### Descric~ao

Worker respons'avel por carregar dados do banco SQLite de forma ass'incrona, com suporte a paginac~ao e ordenac~ao segura.

### Localcza?~ao

`gui/workers/data_loader_worker.py`

### Classe: `DataLoaderWorker`

Herda de: `PyQt6.QtCore.QThread`

#### Sinais

| Sinal | Tipo | Descric~ao |
|-------|------|-----------|
| `data_loaded` | `pyqtSignal(pd.DataFrame)` | Emitido quando dados s~ao carregados com sucesso |
| `error_occurred` | `pyqtSignal(str)` | Emitido quando ocorre um erro durante o carregamento |

#### Atributos de Classe

| Atributo | Tipo | Descric~ao |
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
    offset: int = 0,        # Offset para paginac~ao
    order_by: str | None = None  # Cl'ausula ORDER BY
)
```

#### M'etodos P'ublicos

##### `cancel() -> None`

Solicita cancelamento do worker.

```python
worker = DataLoaderWorker("ssas.db", "ssa_table")
worker.start()
# ... posteriormente
worker.cancel()  # Solicita interrupc~ao segura
```

**Thread-Safe**: Sim
**Bloqueante**: N~ao

#### M'etodos Protegidos

##### `_is_cancelled() -> bool`

Verifica se o worker foi cancelado.

**Retorna**: `True` se cancelado, `False` caso contr'ario

##### `_sanitize_identifier(value: str) -> str`

Remove caracteres perigosos de identificadores SQL.

**Protec~ao**: SQL Injection
**Retorna**: String sanitizada ou vazia se inv'alido

##### `_quote_identifier(value: str) -> str`

Escapa identificadores SQL com aspas.

**Exemplo**: `ssa_table` -> `"ssa_table"`

##### `_resolve_target_table() -> str`

Resolve o nome da tabela alvo, com fallback para "ssa_table".

**L'ogica**:
1. Verifica se tabela solicitada existe
2. Se n~ao existe, tenta "ssa_table"
3. Retorna fallback se nenhuma existe

##### `_normalize_order_by(order_by: str | None) -> str | None`

Normaliza e valida cl'ausula ORDER BY.

**Validac~oes**:
- Colunas devem estar na whitelist
- Direc~ao deve ser ASC ou DESC
- Previne SQL injection

**Excec~oes**:
- `ValueError`: ORDER BY inv'alido ou coluna n~ao permitida

#### Exemplos de Uso

### Exemplo 1: Carregamento B'asico

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

### Exemplo 2: Paginac~ao

```python
# Carregar p'agina 3 com 50 registros por p'agina
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

# Se usu'ario cancelar operac~ao
if user_cancelled:
    worker.cancel()
    worker.wait(timeout=5000)  # Esperar at'e 5 segundos
```

---

## FilterWorker

### Descric~ao

Work'ar respons?vel por filtrar DataFrames de forma ass'incrona, com cache LRU inteligente.

### Localizac~ao

`gui/workers/filter_worker.py`

### Classe: `FilterWorker`

Herda de: `PyQt6.QtCore.QThread`

#### Sinais

| Sinal | Tipo | Descric~ao |
|-------|------|-----------|
| `filter_finished` | `pyqtSignal(pd.DataFrame)` | Emitido com resultado da filtragem |
| `error_occurred` | `pyqtSignal(str)` | Emitido quando ocorre erro na filtragem |

#### Atributos de Classe

| Atributo | Tipo | Descric~ao |
|----------|------|-----------|
| `_cache` | `FilterCache` | Cache LRU compartilhado entre inst^ancias |

#### Construtor

```python
def __init__(
    self,
    df_completo: pd.DataFrame,     # DataFrame a ser filtrado
    search_chunks: list,           # Lista de chunks de busca
    default_mode: str = 'contains',  # Modo de busca padr~ao
    cache_context: str | None = None  # Contexto adicional para chave de cache
)
```

#### M'etodos P'ublicos

##### `cancel() -> None`

Solicita cancelamento do worker.

```python
worker = FilterWorker(df, [["termo1"], ["termo2"]])
worker.start()
worker.cancel()  # Cancela processamento
```

##### `_build_df_hash(df_completo: pd.DataFrame) -> str`

**M'etodo Est'atico**

Cria hash estrutural do DataFrame para chave de cache.

**Algoritmo de Amostragem**:
- DataFrames <= 24 linhas: Usa DataFrame completo
- DataFrames > 24 linhas: Amostra estratificada (head + mid + tail)

**Retorna**: Hash hexadecimal de 16 caracteres

**Exemplo**:
```python
df = pd.DataFrame({'col': [1, 2, 3]})
hash_val = FilterWorker._build_df_hash(df)
# Retorna: '84e3d1d94822c03e'
```

#### Exemplos de Uso

### Exemplo 1: Filtragem B'asica

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

### Exemplo 2: M'ultiplos Chunks

```python
# Buscar SSAs que contenham "APV" OU "STE"
worker = FilterWorker(df, [["APV"], ["STE"]])

# Resultado: uni~ao dos filtros (OR l'ogico)
```

### Exemplo 3: Com Cache

```python
# Primeira execuc~ao - cache miss
worker1 = FilterWorker(df, [["test"]], cache_context='{"tab":"main"}')
worker1.start()
worker1.wait()

# Segunda execuc~ao - cache hit (mesmo df_hash e search_chunks)
worker2 = FilterWorker(df, [["test"]], cache_context='{"tab":"main"}')
worker2.start()  # Usa cache, n~ao reprocessa
```

---

## Padr~oes de Uso

### Padr~ao 1: Chain de Workers

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

### Padr~ao 2: Worker com Timeout

```python
worker = DataLoaderWorker("ssas.db", "ssa_table")
worker.start()

# Esperar com timeout
if not worker.wait(timeout=30000):  # 30 segundos
    worker.cancel()
    logger.warning("Worker timeout, cancelado")
```

### Padr~ao 3: Worker Pool

```python
# Executar m'ultiplos workers em paralelo
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

### Boas Pr'aticas

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

### Handlers T'ipicos

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
| `ValueError` | ORDER BY inv'alido | `error_occurred` emitido |
| `TypeError` | Tipo incorreto retornado | `error_occurred` emitido |
| Cancelamento | Usu'ario cancelou | Nenhum sinal emitido |

### Estrat'egia de Retry

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

Localizac~ao: `tests/test_workers_advanced.py`

#### Executar Testes

```bash
# Usando venv do projeto
source .venv/bin/activate
python -m pytest tests/test_workers_advanced.py -v

# Executar apenas testes unit'arios
python -m pytest tests/test_workers_advanced.py::TestDataLoaderWorkerUnit -v

# Executar testes de performance
python -m pytest tests/test_workers_advanced.py::TestWorkerPerformance -v
```

#### Cobertura de Testes

- **TestDataLoaderWorkerUnit**: 9 testes
  - Sanitizac~ao de identificadores
  - Normalizac~ao de ORDER BY
  - Resoluc~ao de tabela

- **TestDataLoaderWorkerIntegration**: 6 testes
  - Emiss~ao de signals
  - Cancelamento
  - Paginac~ao

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
  - Concorr^encia

**Total**: 35 testes cobrindo 100% dos m'etodos p'ublicos

---

## Refer^encias

### Arquivos Relacionados

- `gui/workers/data_loader_worker.py` - Implementac~ao do DataLoaderWorker
- `gui/workers/filter_worker.py` - Implementac~ao do FilterWorker
- `gui/workers/rescan_worker.py` - Implementac~ao do RescanWorker
- `gui/cache/filter_cache.py` - Implementac~ao do cache LRU
- `tests/test_workers_advanced.py` - Suite de testes completa

### Documentac~ao Externa

- [PyQt6 QThread](https://doc.qt.io/qtforpython-6/PyQt6/QtCore/QThread.html)
- [PyQt6 Signals & Slots](https://doc.qt.io/qtforpython-6/overviews/signalsandslots.html)
- [Pandas DataFrame](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.html)

---

## Changelog

### v2.0.0 (2025-02-23)
- Adicionada suite de testes avancada (35 testes)
- Documentac~ao t?cnica completa das APIs
- Testes de performance e regress~ao

### v1.0.0 (2025-02-20)
- Implementac~ao inicial dos workers
- Cache LRU para FilterWorker
- Protec~ao SQL injection no DataLoaderWorker

---

*Documentac~ao gerada automaticamente para o branch `codex/dev-filtros-stability`*
