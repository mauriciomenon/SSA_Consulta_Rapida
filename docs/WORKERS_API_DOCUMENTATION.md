# Documentação Técnica - Workers Assíncronos da GUI

## Visão Geral

## Contrato atual de ciclo de vida

- `closeEvent` restaura `_is_shutting_down=False` ao adiar o fechamento e mantem
  timers operantes. `shutdown()` solicita cancelamento e consulta o estado real
  dos workers, sem esperas em serie na GUI.
- Preferencias usam `flush(timeout=1.0)` enquanto a janela pode permanecer
  aberta; o gravador continua aceitando atualizacoes. Seu encerramento so e
  solicitado depois de aceitar o fechamento da janela.
- O prazo de 30 segundos e reiniciado quando as operacoes pendentes nao incluem
  nenhuma da tentativa anterior. Workers Qt e a thread de derivadas participam
  dessa identidade; prazo expirado nao e evidencia de conclusao com sucesso.
- A validacao de banco conserva resultado e `_request_id` por requisicao.
  Retornos antigos nao alteram a selecao atual nem seu estado de ocupacao.
- Menus de operacoes sobre o banco usam o estado compartilhado em
  `gui/ssa/app_menus.py`, incluindo a vida real da thread de derivadas. Uma
  finalizacao antiga nao libera uma operacao nova.
- `RescanWorker` propaga as ressalvas reais do relatorio de integridade, sem
  repetir a verificacao apenas para mudar a mensagem final.
- O ultimo relatorio manual valido de derivadas pode ser exportado pela GUI;
  seu ciclo de invalidacao e formatos estao no [guia de derivadas](DERIVADAS_SYNC_RUNBOOK.md).

Detalhes e criterios de regressao:
[guardrails da GUI](GUI_ASYNC_LOADING_GUARDRAILS.md) e
[plano de validacao](VALIDATION_PLAN.md).

## Historico: atualizacao 2026-03-27

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
2. **Cancelamento cooperativo**: workers Qt oferecem `cancel()` ou `requestInterruption()` conforme sua interface. Solicitar cancelamento nao comprova termino; uma leitura de planilha em andamento pode concluir antes da proxima verificacao.
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
| `data_prepared` | `pyqtSignal(object)` | Entrega o resultado preparado para a GUI |
| `data_loaded` | `pyqtSignal(pd.DataFrame)` | Emitido quando dados são carregados com sucesso |
| `error_occurred` | `pyqtSignal(str)` | Emitido quando ocorre um erro durante o carregamento |

#### Responsabilidades extraidas

O worker delega consulta e validacao SQL a `data_loader_query.py`, resolucao de
tabelas e colunas a `data_loader_repository.py`, e preparo de dados a
`data_loader_processing.py`. Identificadores e ordenacao nao devem ser tratados
por metodos antigos atribuidos diretamente a `DataLoaderWorker`.

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

A validacao de identificadores e `ORDER BY` pertence a
`gui/workers/data_loader_query.py`. A resolucao da tabela pertence a
`gui/workers/data_loader_repository.py`; consultar esses modulos para os
contratos atuais, sem recriar os metodos que foram extraidos do worker.

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
    # Manter referencia ate finished; nao aguardar na thread da GUI.
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
    search_chunks: list | tuple,  # Grupos de termos
    search_columns: list[str] | None = None,  # Colunas de busca
    default_mode: str = 'contains',  # Modo de busca
    cache_context: str | None = None,  # Contexto da chave
    df_hash: str | None = None,      # Hash calculado anteriormente
    cache: FilterCache | None = None  # Cache da instancia ou compartilhado
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

A implementacao delega a `core.dataframe_fingerprint.build_dataframe_filter_hash`.
O hash participa da chave junto dos termos e do contexto; nao depender de uma
amostra fixa ou de um valor literal de hash no codigo consumidor.

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

### Reuso do cache

Uma segunda filtragem pode reutilizar o resultado quando o primeiro worker
terminou e o hash do DataFrame, os termos, as colunas e o contexto permanecem
compativeis. Iniciar dois workers em sequencia nao garante que o primeiro ja
preencheu o cache. Encadear a nova requisicao pelo controlador e por `finished`,
sem `wait()` na thread da GUI.

---

## Padroes de uso na GUI

- Conectar sinais antes de iniciar; reter o worker enquanto estiver ativo.
- Encadear carga e filtro pelo resultado da requisicao vigente. Um worker local
  sem referencia retida pode ser destruido antes do fim.
- Tratar falha de `start()` no mesmo controlador que marcou a operacao como
  ativa, liberando o estado e informando a falha.
- Trocar workers sem esperar na thread da GUI; resultados e `finished` de
  requisicoes antigas nao podem atualizar a interface da atual.
- Um timeout solicita cancelamento e informa a falha, mas nao autoriza destruir
  o worker que continua vivo. Preservar a referencia ate o termino nativo.
- Para multiplas cargas, usar o controle existente em `gui/ssa/gui_workers.py`.
  Nao copiar exemplos de espera ilimitada ou criar uma fila paralela na janela.

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

### Repeticao apos falha

Nao reiniciar automaticamente o mesmo worker em um loop bloqueante. Uma nova
operacao precisa de identidade propria, conexoes sem acumulo e tratamento da
falha anterior. O controlador decide se a repeticao e permitida; cancelamento
ou timeout nao equivalem a sucesso nem justificam esconder o erro.

---

## Testes

### Suite de Testes

Localização: `tests/test_workers_advanced.py`

#### Executar Testes

```bash
# Usar o ambiente existente do projeto
uv run --no-sync python -m pytest tests/test_workers_advanced.py -v

# Executar apenas testes unitários
uv run --no-sync python -m pytest tests/test_workers_advanced.py::TestDataLoaderWorkerUnit -v

# Executar testes de performance
uv run --no-sync python -m pytest tests/test_workers_advanced.py::TestWorkerPerformance -v
```

#### Inventario historico de testes

As contagens abaixo sao do inventario original, nao da ultima execucao. Para
validacao atual, registrar coleta, resultado e revisao conforme
[VALIDATION_PLAN.md](VALIDATION_PLAN.md).

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

O inventario historico nao comprova cobertura atual nem execucao dos caminhos
novos. Nao atribuir cobertura de 100% sem medicao da revisao validada.

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

*O historico acima registra versoes anteriores; o contrato atual esta no inicio
deste documento e nos guardrails vinculados.*

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->

