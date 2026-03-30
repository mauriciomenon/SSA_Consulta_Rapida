# Arquitetura de Workers - Diagrama de Sequência e Fluxo

## Diagrama de Sequência - Carregamento e Filtragem

```mermaid
sequenceDiagram
    participant UI as SSAMainWindow
    participant DL as DataLoaderWorker
    participant DB as SQLite DB
    participant FW as FilterWorker
    participant Cache as FilterCache
    participant App as app_logic

    UI->>DL: __init__(db_path, table_name)
    UI->>DL: data_loaded.connect(on_data_loaded)
    UI->>DL: error_occurred.connect(on_error)
    UI->>DL: start()
    
    activate DL
    DL->>DL: run()
    DL->>DL: _resolve_target_table()
    DL->>DL: _normalize_order_by(order_by)
    DL->>DB: query_db(...)
    DB-->>DL: pd.DataFrame
    DL->>DL: _is_cancelled()
    DL-->>UI: data_loaded.emit(df)
    deactivate DL
    
    UI->>UI: on_data_loaded(df)
    UI->>FW: __init__(df, search_chunks)
    UI->>FW: filter_finished.connect(on_filter_finished)
    UI->>FW: start()
    
    activate FW
    FW->>FW: run()
    FW->>FW: _build_df_hash(df)
    FW->>Cache: get(hash, chunks, mode)
    
    alt Cache Hit
        Cache-->>FW: cached DataFrame
    else Cache Miss
        FW->>App: parse_search_terms()
        FW->>App: filter_dataframe()
        FW->>Cache: put(hash, chunks, mode, result)
    end
    
    FW-->>UI: filter_finished.emit(df_filtrado)
    deactivate FW
```

## Diagrama de Classes

```mermaid
classDiagram
    class QThread {
        +start()
        +wait()
        +requestInterruption()
        +isInterruptionRequested()
    }
    
    class DataLoaderWorker {
        +data_loaded: pyqtSignal
        +error_occurred: pyqtSignal
        -db_path: str
        -table_name: str
        -limit: int
        -offset: int
        -order_by: str
        -_cancel_requested: bool
        +cancel()
        +run()
        -_is_cancelled()
        -_sanitize_identifier()
        -_quote_identifier()
        -_resolve_target_table()
        -_normalize_order_by()
    }
    
    class FilterWorker {
        +filter_finished: pyqtSignal
        +error_occurred: pyqtSignal
        -_cache: FilterCache
        -df_completo: pd.DataFrame
        -search_chunks: list
        -default_mode: str
        -cache_context: str
        -df_hash: str
        +cancel()
        +run()
        -_is_cancelled()
        +_build_df_hash()
    }
    
    class FilterCache {
        -max_size: int
        -_cache: OrderedDict
        -_lock: threading.Lock
        +get()
        +put()
        +clear()
        -_generate_key()
    }
    
    QThread <|-- DataLoaderWorker
    QThread <|-- FilterWorker
    FilterWorker ..> FilterCache : uses
```

## Fluxograma - Algoritmo de Hash do FilterWorker

```mermaid
flowchart TD
    A[Início: _build_df_hash] --> B{df_completo é None?}
    B -->|Sim| C[Retornar hash de 'none']
    B -->|Não| D{row_count <= 24?}
    D -->|Sim| E[Usar DataFrame completo]
    D -->|Não| F[Amostragem estratificada]
    F --> G[head: 8 linhas]
    F --> H[mid: 8 linhas]
    F --> I[tail: 8 linhas]
    G --> J[Concatenar amostras]
    H --> J
    I --> J
    E --> K[Criar payload]
    J --> K
    K --> L[shape + columns + dtypes + records]
    L --> M[MD5 do payload]
    M --> N[Retornar hash 16 chars]
    C --> O[Fim]
    N --> O
```

## Fluxograma - Cancelamento Seguro

```mermaid
flowchart LR
    A[Usuário chama cancel] --> B[_cancel_requested = True]
    B --> C[requestInterruption]
    C --> D{run está executando?}
    D -->|Sim| E[_is_cancelled?]
    E -->|Sim| F[Retornar early]
    E -->|Não| G[Continuar processamento]
    D -->|Não| H[Não faz nada]
    
    style A fill:#f9f,stroke:#333,stroke-width:2px
    style F fill:#f99,stroke:#333,stroke-width:2px
```

## Diagrama de Estados - DataLoaderWorker

```mermaid
stateDiagram-v2
    [*] --> Idle: __init__
    Idle --> Running: start()
    Running --> Completed: run() finalizado
    Running --> Cancelled: cancel()
    Running --> Error: Exceção
    Completed --> Idle: wait() retorna
    Cancelled --> Idle: wait() retorna
    Error --> Idle: error_occurred.emit()
    
    note right of Running
        Verifica _is_cancelled()
        periodicamente durante execução
    end note
```

## Mapa de Cache LRU

```mermaid
flowchart LR
    subgraph "Cache Hit"
        A[Chave: hash+chunks+mode] --> B{Existe no cache?}
        B -->|Sim| C[Retornar cópia]
        C --> D[Mover para final]
    end
    
    subgraph "Cache Miss"
        B -->|Não| E[Executar filtro]
        E --> F[Armazenar resultado]
        F --> G{Cache cheio?}
        G -->|Sim| H[Remover mais antigo]
        G -->|Não| I[Adicionar ao final]
        H --> I
    end
```

## Arquitetura de Threads

```mermaid
flowchart TB
    subgraph "Thread Principal (UI)"
        UI[SSAMainWindow]
    end
    
    subgraph "Thread Pool de Workers"
        W1[DataLoaderWorker 1]
        W2[DataLoaderWorker 2]
        WF[FilterWorker]
    end
    
    subgraph "Recursos Compartilhados"
        DB[(SQLite DB)]
        CACHE[(FilterCache)]
    end
    
    UI -->|start| W1
    UI -->|start| W2
    UI -->|start| WF
    
    W1 -->|query| DB
    W2 -->|query| DB
    WF -->|get/put| CACHE
    
    W1 -->|signal| UI
    W2 -->|signal| UI
    WF -->|signal| UI
```

## Casos de Uso

### Caso 1: Carregamento Normal
```mermaid
sequenceDiagram
    User->>UI: Clicar "Carregar Dados"
    UI->>DL: Criar e iniciar
    DL->>DB: Query
    DB-->>DL: Resultado
    DL-->>UI: data_loaded.emit
    UI->>UI: Atualizar tabela
```

### Caso 2: Cancelamento
```mermaid
sequenceDiagram
    User->>UI: Clicar "Cancelar"
    UI->>DL: cancel()
    DL->>DL: _is_cancelled = True
    DL->>DL: run() verifica cancel
    DL->>DL: Retornar early
    DL-->>UI: Thread finaliza
```

### Caso 3: Cache Hit
```mermaid
sequenceDiagram
    User->>UI: Digitar termo de busca
    UI->>FW: Criar worker
    FW->>Cache: get()
    Cache-->>FW: Resultado cacheado
    FW-->>UI: filter_finished.emit
    Note over FW: Nenhum processamento
```

### Caso 4: Cache Miss
```mermaid
sequenceDiagram
    User->>UI: Digitar novo termo
    UI->>FW: Criar worker
    FW->>Cache: get()
    Cache-->>FW: None
    FW->>App: Filtrar dados
    FW->>Cache: put()
    FW-->>UI: filter_finished.emit
```

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->

