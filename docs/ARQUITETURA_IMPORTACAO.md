# Arquitetura do Sistema de Importação SSA_Consulta_Rapida

## Visão Geral

O sistema de importação do SSA_Consulta_Rapida é uma arquitetura multi-camadas projetada para importar dados de planilhas Excel (formato AMS) para um banco SQLite com alta resiliência, performance e capacidade de recuperação de erros.

## 1. Arquitetura em Camadas

### 1.1 Diagrama de Arquitetura (Camadas)

```
┌─────────────────────────────────────────────────────────────┐
│                    CAMADA DE INTERFACE                      │
├─────────────────────────────────────────────────────────────┤
│  GUI (PyQt6)        │        CLI (Terminal)                 │
│  gui/gui_ssa.py     │        interface/cli.py               │
│  gui/workers.py     │        interface/command_handlers.py  │
└─────────────────────┴───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  CAMADA DE ORQUESTRAÇÃO                     │
├─────────────────────────────────────────────────────────────┤
│  core/app_logic.py                                          │
│  - run_importer_logic()                                     │
│  - _import_single_file()                                    │
│  - Gerenciamento de cache                                   │
│  - Sincronização de derivadas                               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   CAMADA DE EXTRAÇÃO                        │
├─────────────────────────────────────────────────────────────┤
│  extracao/extractor.py                                      │
│  - extract_data_from_excel()                                │
│  - Interface única para ingestão                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              CAMADA DE PROCESSAMENTO ROBUSTO                │
├─────────────────────────────────────────────────────────────┤
│  Modo Atual (v3.0):                                         │
│  ├─ utils/robust_importer.py                                │
│  │  └─ import_excel_robust()                                │
│  │     ├─ Detecção heurística de cabeçalhos                 │
│  │     ├─ Mapeamento de colunas (aliases)                   │
│  │     ├─ Normalização SSA                                  │
│  │     ├─ Parsing de datas                                  │
│  │     ├─ Coalescência de colunas                           │
│  │     └─ Deduplicação                                      │
│  │                                                          │
│  └─ utils/enhanced_importer.py (format detection)           │
│     └─ EnhancedAMSImporter                                  │
│        ├─ detect_format()                                   │
│        └─ import_with_format_detection()                    │
│                                                              │
│  Legado (referência):                                       │
│  └─ utils/robust_importer_old.py (não usado)                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  CAMADA DE PERSISTÊNCIA                     │
├─────────────────────────────────────────────────────────────┤
│  Modo Otimizado (padrão):                                   │
│  ├─ armazenamento/database_optimized.py                     │
│  │  └─ insert_dataframe_optimized()                         │
│  │     ├─ WAL mode                                          │
│  │     ├─ Batch inserts                                     │
│  │     ├─ Pragmas de performance                            │
│  │     └─ smart_upsert                                      │
│  │                                                          │
│  Modo Padrão:                                               │
│  ├─ armazenamento/database.py                               │
│  │  └─ insert_dataframe_with_smart_upsert()                 │
│  │                                                          │
│  Fallback Emergencial:                                      │
│  └─ utils/fallback/emergency_import.py                      │
│     └─ Sem dependências pesadas (SQLite puro)               │
└─────────────────────────────────────────────────────────────┘
```

## 2. Fluxo de Dados Detalhado

### 2.1 Sequência de Importação

```
┌──────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  Usuário │────▶│  main.py         │────▶│  run_importer_logic │
│  /CLI/GUI│     │  --force-rescan  │     │  (core/app_logic)   │
└──────────┘     └──────────────────┘     └──────────┬──────────┘
                                                     │
                         ┌───────────────────────────┼───────────────────────────┐
                         │                           │                           │
                         ▼                           ▼                           ▼
              ┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
              │ caching.py       │      │ Arquivos         │      │ Derivadas        │
              │ get_files_to_    │      │ Excel            │      │ Sync             │
              │ process()        │      │ (.xlsx)          │      │ (derivadas_sync) │
              └────────┬─────────┘      └────────┬─────────┘      └──────────────────┘
                       │                         │
                       └───────────┬─────────────┘
                                   │
                                   ▼
                        ┌────────────────────┐
                        │  extractor.py      │
                        │  extract_data_     │
                        │  from_excel()      │
                        └────────┬───────────┘
                                 │
                                 ▼
                        ┌────────────────────┐
                        │  robust_importer   │
                        │  import_excel_     │
                        │  robust()          │
                        └────────┬───────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
              ▼                  ▼                  ▼
      ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
      │  Detecção    │  │  Mapeamento  │  │  Validação   │
      │  Cabeçalho   │  │  Colunas     │  │  Dados       │
      └──────────────┘  └──────────────┘  └──────────────┘
              │                  │                  │
              └──────────────────┼──────────────────┘
                                 │
                                 ▼
                        ┌────────────────────┐
                        │  database_         │
                        │  optimized.py      │
                        │  insert_dataframe  │
                        │  _optimized()      │
                        └────────────────────┘
```

### 2.2 Estados do Processo de Importação

```
                    ┌─────────────────┐
                    │     INÍCIO      │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Verificar Cache │
                    │  (caching.py)   │
                    └────────┬────────┘
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                 │
           ▼                 ▼                 ▼
    ┌────────────┐   ┌────────────┐   ┌────────────┐
    │ Arquivos   │   │ Cache      │   │ Force      │
    │ novos      │   │ modificado │   │ Rescan     │
    └─────┬──────┘   └─────┬──────┘   └─────┬──────┘
          │                │                │
          └────────────────┼────────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │  Para cada      │
                  │  arquivo...     │
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │  Extrair        │
                  │  (extractor)    │
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │  Validar        │
                  │  (validate_df)  │
                  └────────┬────────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
    ┌────────────┐  ┌────────────┐  ┌────────────┐
    │  Válido    │  │ Inválido   │  │ Cancelado  │
    │            │  │ (log erro) │  │ (abortar)  │
    └─────┬──────┘  └────────────┘  └────────────┘
          │
          ▼
┌─────────────────┐
│  Inserir DB     │
│  (optimized)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Atualizar      │
│  Cache          │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│     FIM         │
└─────────────────┘
```

## 3. Componentes Detalhados

### 3.1 robust_importer.py (Núcleo de Importação)

**Função**: `import_excel_robust(file_path, mappings_path, drop_empty_numero_ssa, deduplicate)`

**Heurísticas Implementadas**:
1. **Detecção de Header Mesclado**: Identifica quando há um título abrangendo a primeira linha
2. **Scan Multi-Linha**: Procura cabeçalhos reais nas primeiras 10-15 linhas
3. **Fallback de Coluna Única**: Quando só há 1 coluna detectada, reinterpreta primeira linha
4. **Promoção Explícita**: Garante existência da coluna 'numero_ssa' via aliases
5. **Coalescência**: Une colunas duplicadas semanticamente

**Normalizações**:
- Cabeçalhos: remoção de acentos, quebras de linha, espaços extras
- Números SSA: remove `.0` de floats, valida formato
- Datas: parsing de texto + serial Excel via `parse_any_date()`

**Estatísticas Coletadas**:
- total_rows_in/out
- mapped_columns_count
- dropped_columns
- merged_columns
- date_parse_failures
- duplicate_rows_dropped
- invalid_numero_ssa_rows
- header_candidate_lines_considered
- selected_header_line_index
- alias_hits

### 3.2 database_optimized.py (Persistência Otimizada)

**Otimizações SQLite**:
```sql
PRAGMA journal_mode=WAL;        -- Leituras concorrentes
PRAGMA synchronous=NORMAL;      -- Balanço segurança/velocidade
PRAGMA cache_size=10000;        -- Cache maior
PRAGMA temp_store=MEMORY;       -- Temp em RAM
PRAGMA mmap_size=268435456;     -- Memory-mapped I/O (256MB)
```

**Estratégia de Inserção**:
1. Normalização de IDs SSA (evita artefatos decimais)
2. Validação de identificadores canônicos
3. Conversão vetorizada de datas
4. Chunking automático (limite 999 variáveis SQLite)
5. Smart upsert (INSERT OR REPLACE)

**Função**: `insert_dataframe_optimized(df, db_path, table_name)`

### 3.3 app_logic.py (Orquestração)

**Função Principal**: `run_importer_logic(docs_dir, db_path, cache_file, force_import, progress_callback)`

**Fluxo Interno**:
1. Resolve caminhos com validação de segurança (`path_safety.py`)
2. Descobre arquivos via cache ou força reimportação
3. Processa arquivos regulares (Excel padrão)
4. Processa planilhas especiais de derivadas
5. Executa sincronização de derivadas (DB-only se necessário)
6. Valida consistência de dados
7. Atualiza cache

**Tratamento de Erros**:
- Hierarquia de exceções customizadas:
  - `ImporterError` (base)
  - `CacheError`
  - `ExtractionError`
  - `DatabaseError` (com subclasses)
  - `DataValidationError`

### 3.4 Sistema de Cache (caching.py)

**Objetivo**: Evitar reimportação de arquivos não modificados

**Mecanismo**:
- Arquivo `.last_import` JSON
- Chave: caminho do arquivo
- Valor: timestamp de modificação + hash

**Funções**:
- `get_all_xlsx_files(docs_dir)`
- `get_files_to_process(docs_dir, cache_file)`
- `update_import_cache(processed_files, cache_file)`

## 4. Interfaces de Uso

### 4.1 CLI (Command Line Interface)

**Comandos Disponíveis**:
```bash
# Importação normal
python main.py

# Forçar reimportação
python main.py --force-rescan

# Pular importação (usar DB existente)
python main.py --skip-import

# Apenas CLI (sem GUI)
python main.py --cli

# Limpar tudo e recriar
python main.py --clear-all
```

**Fluxo CLI**:
1. Parse de argumentos
2. Configuração de logging
3. Execução de `run_importer_logic()`
4. Inicialização da interface CLI interativa

### 4.2 GUI (Graphical User Interface)

**PyQt6 Components**:
- `gui/gui_ssa.py`: Janela principal
- `gui/workers.py`: Workers assíncronos (DataLoader, Filter)
- `gui/ssa/gui_workers.py`: Workers de reescaneamento
- `gui/cache.py`: Sistema de cache de filtros

**Processo de Importação na GUI**:
1. Botão "Reimportar" aciona `RescanWorker`
2. Worker executa `run_importer_logic()` em thread separada
3. Progresso reportado via sinais Qt
4. Cancelamento via flag `should_cancel`
5. Resultado exibido em diálogo modal

## 5. Diagrama de Classes

```
┌────────────────────────────────────────────────────────────────┐
│                        CLASSES PRINCIPAIS                      │
└────────────────────────────────────────────────────────────────┘

┌────────────────────┐
│   <<dataclass>>    │
│   ImportStats      │
├────────────────────┤
│ total_rows_in: int │
│ total_rows_out: int│
│ original_columns_  │
│   count: int       │
│ mapped_columns_    │
│   count: int       │
│ dropped_columns:   │
│   List[str]        │
│ merged_columns:    │
│   Dict[str,List]   │
│ date_parse_        │
│   failures: Dict   │
│ duplicate_rows_    │
│   dropped: int     │
│ invalid_numero_    │
│   ssa_rows: int    │
│ file_path: str     │
│ header_candidate_  │
│   lines_considered │
│ selected_header_   │
│   line_index       │
│ alias_hits: int    │
├────────────────────┤
│ to_dict() -> Dict  │
└────────────────────┘

┌────────────────────┐
│ EnhancedAMSImporter│
├────────────────────┤
│ known_formats: Dict│
├────────────────────┤
│ detect_format(df)  │
│ safe_column_       │
│   addition()       │
│ import_with_format_│
│   detection()      │
│ _apply_format_     │
│   transformations()│
└────────────────────┘

┌────────────────────┐
│ RescanWorker       │
│ (PyQt6 QThread)    │
├────────────────────┤
│ progress: pyqtSignal│
│ finished: pyqtSignal│
│ error: pyqtSignal  │
├────────────────────┤
│ __init__()         │
│ run()              │
│ cancel()           │
└────────────────────┘

┌────────────────────┐
│ DataLoaderWorker   │
│ (PyQt6 QThread)    │
├────────────────────┤
│ data_ready: Signal │
│ error: Signal      │
├────────────────────┤
│ __init__(query)    │
│ run()              │
└────────────────────┘

┌────────────────────┐
│ <<module>>         │
│ robust_importer    │
├────────────────────┤
│ _canonicalize_     │
│   header()         │
│ _build_alias_      │
│   mapping()        │
│ _coalesce_columns()│
│ _clean_numero_ssa_ │
│   series()         │
│ _parse_single_date()│
│ import_excel_      │
│   robust()         │
└────────────────────┘
```

## 6. Erros Conhecidos e Problemas Críticos

### 6.1 Erros Crassos Identificados

1. **Vulnerabilidade de Path Traversal** (Potencial)
   - **Localização**: `app_logic.py`, funções que recebem caminhos de arquivo
   - **Problema**: Sem validação rigorosa de caminhos antes de operações de arquivo
   - **Mitigação**: Uso de `ensure_path_is_allowed()` em `_resolve_import_targets()`

2. **Race Condition em Cache**
   - **Localização**: `caching.py`
   - **Problema**: Múltiplos processos podem corromper o arquivo `.last_import`
   - **Impacto**: Perda de informações de cache
   - **Mitigação**: Nenhuma (não implementado locking)

3. **Consumo Excessivo de Memória em Arquivos Grandes**
   - **Localização**: `robust_importer.py`
   - **Problema**: Carrega arquivo Excel inteiro em memória
   - **Impacto**: OOM em arquivos > 100MB
   - **Mitigação**: Chunking no database_optimized, mas não no leitor Excel

4. **Dependência Circular Fragil**
   - **Localização**: `database_optimized.py` ↔ `database.py`
   - **Problema**: Importação lazy que pode quebrar se ordem mudar
   - **Nota**: Documentada no código: "if get_db_connection moves lower in database.py, circular import will break"

5. **Perda de Dados em Cancelamento**
   - **Localização**: `app_logic.py`, `_import_single_file()`
   - **Problema**: Cancelamento entre validação e inserção pode deixar dados parciais
   - **Impacto**: Inconsistência no banco
   - **Mitigação**: Verificação `should_cancel` múltiplas vezes, mas não é transacional

### 6.2 Problemas de Performance

1. **Leitura Excel Não-Chunked**
   - `pd.read_excel()` carrega tudo na memória
   - Não há processamento stream
   - Impacto severo em arquivos grandes

2. **Releitura de Arquivos**
   - `robust_importer` pode reler o mesmo arquivo até 3x:
     1. Leitura inicial
     2. Detecção de header mesclado
     3. Scan de header multi-linha

3. **Validação Linha-a-Linha**
   - Loops Python para normalização de SSA
   - Não vetorizado via pandas
   - Ponto de estrangulamento em datasets grandes

4. **Upsert Não-Batch**
   - Smart upsert pode executar uma query por linha em caso de conflito
   - Deveria usar INSERT OR REPLACE em batch

### 6.3 Problemas de Confiabilidade

1. **Parsing de Datas Não-Determinístico**
   - `parse_any_date()` tenta múltiplos formatos
   - Pode interpretar 02/03/2025 como 2 de Março ou 3 de Fevereiro
   - Depende de configuração regional

2. **Detecção de Formatos Heurística**
   - Baseada em palavras-chave ("Todas as SSAs", "Em Execução")
   - Fácil de quebrar com variações de nomenclatura
   - Sem fallback robusto

3. **Falta de Checksum de Arquivo**
   - Cache usa apenas timestamp de modificação
   - Arquivos podem ter conteúdo diferente com mesmo timestamp
   - Não detecta corrupção de arquivo

4. **Tratamento Inconsistente de Encoding**
   - Excel pode ter encoding diferente do esperado
   - Acertos/graves podem causar mapeamento incorreto
   - Não há detecção automática de encoding

### 6.4 Problemas de Validação

1. **Validação de Schema Limitada**
   - Não valida tipos de dados antes da inserção
   - Campos obrigatórios são verificados, mas tipos não
   - SQLite é flexível demais (aceita qualquer tipo)

2. **Falta de Validação de Referências**
   - Não verifica se `derivada_de` aponta para SSA existente
   - Permite referências órfãs
   - Sincronização de derivadas é processo separado

3. **Validação de Datas Incompleta**
   - Aceita datas futuras distantes
   - Não valida se data_cadastro <= data_limite
   - Sem validação de dias úteis

## 7. Pontos Fortes (Coisas Boas)

### 7.1 Arquitetura

1. **Separação de Responsabilidades Clara**
   - Extrator → Processador → Persistidor
   - Facilita testes e manutenção

2. **Sistema de Exceções Hierárquico**
   - Erros bem categorizados
   - Facilita tratamento específico

3. **Fallbacks Múltiplos**
   - Emergency import (sem pandas)
   - Modo otimizado vs padrão
   - Versões antigas como referência

### 7.2 Robustez

1. **Tolerância a Variações de Cabeçalho**
   - Heurísticas múltiplas para detecção
   - Normalização agressiva
   - Coalescência de colunas sinônimas

2. **Não-Interrupção por Erros de Linha**
   - Continua processando mesmo com linhas inválidas
   - Registra estatísticas de falhas
   - Reporta amostras de problemas

3. **Cancelamento Cooperativo**
   - Flag `should_cancel` verificada em múltiplos pontos
   - Permite interromper sem corromper estado
   - Integrado com GUI (botão cancelar)

### 7.3 Performance (quando bem configurado)

1. **Modo WAL do SQLite**
   - Permite leituras durante importação
   - Melhor concorrência
   - Recuperação mais rápida após crash

2. **Batch Inserts**
   - Reduz round-trips ao banco
   - Configurável via chunk size
   - Respeita limite de 999 variáveis SQLite

3. **Cache de Arquivos**
   - Evita reprocessamento desnecessário
   - Melhora tempo de inicialização

### 7.4 Observabilidade

1. **Logging Detalhado**
   - Múltiplos níveis (DEBUG, INFO, WARNING, ERROR)
   - Contexto em todas as operações
   - Arquivos de log rotativos

2. **Estatísticas Compreensivas**
   - Contadores de linhas/colunas
   - Métricas de deduplicação
   - Falhas de parsing
   - Hits de aliases

3. **Relatório de Validação**
   - Reporta violações por tipo
   - Mostra amostras de SSAs problemáticas
   - Diferencia severidade (warning vs error)

## 8. Métricas de Performance

### 8.1 Benchmarks Esperados

**Hardware de Referência**: SSD, 16GB RAM, CPU moderna

| Cenário | Tempo | Memória | Observações |
|---------|-------|---------|-------------|
| 1 arquivo, 1K linhas | ~2s | ~100MB | Cache miss |
| 1 arquivo, 10K linhas | ~8s | ~200MB | Cache miss |
| 1 arquivo, 100K linhas | ~60s | ~1GB | Cache miss, pode OOM |
| 10 arquivos, 1K cada | ~15s | ~150MB | Batch process |
| Cache hit (sem alterações) | ~0.5s | ~50MB | Apenas verificação |
| Reimportação forçada | Mesmo acima | Mesmo acima | Ignora cache |

### 8.2 Gargalos Identificados

1. **I/O Bound**: Leitura Excel (openpyxl)
2. **CPU Bound**: Normalização SSA linha-a-linha
3. **Memory Bound**: DataFrames pandas grandes
4. **DB Bound**: SQLite em disco (mitigado por WAL)

## 9. Recomendações de Melhoria

### 9.1 Curto Prazo (Quick Wins)

1. **Implementar Chunking na Leitura Excel**
   - Usar `pd.read_excel(..., chunksize=...)`
   - Processar em batches de 5000 linhas
   - Reduzir uso de memória em 80%

2. **Vetorizar Normalização SSA**
   - Usar `pd.Series.apply()` em vez de loop
   - Ou implementar em NumPy
   - Ganho esperado: 10x mais rápido

3. **Adicionar Checksum ao Cache**
   - Calcular MD5 dos primeiros 8KB
   - Detectar alterações de conteúdo
   - Prevenir reimportação de arquivos idênticos

4. **Lock de Arquivo para Cache**
   - Usar `filelock` ou similar
   - Prevenir corrupção em paralelo
   - Essencial para uso multi-usuário

### 9.2 Médio Prazo

1. **Sistema de Schema Versionado**
   - Versionar estrutura do banco
   - Migrações automáticas
   - Validação estrita de tipos

2. **Importação Paralela**
   - Processar múltiplos arquivos em paralelo
   - Limitar concorrência (pool de workers)
   - Cuidado com SQLite (não suporta escritas paralelas)

3. **Pré-validação de Arquivos**
   - Verificar encoding antes de processar
   - Detectar colunas obrigatórias ausentes
   - Falhar rápido com mensagens claras

4. **Compressão de Cache**
   - Usar msgpack ou parquet para cache
   - Reduzir tamanho em 50-70%
   - Melhorar tempo de carregamento

### 9.3 Longo Prazo (Arquitetura)

1. **Migração para Banco Cliente/Servidor**
   - PostgreSQL ou similar
   - Suporte a escritas paralelas reais
   - Melhor performance em grande volume

2. **Sistema de Filas**
   - Importações assíncronas via fila
   - Retry automático com backoff
   - Notificações de conclusão

3. **Web Interface**
   - Upload via browser
   - Drag-and-drop
   - Preview antes de importar

4. **Machine Learning para Detecção de Formatos**
   - Classificador de layout de planilhas
   - Mais robusto que heurísticas
   - Aprende com novos formatos

## 10. Conclusão

O sistema de importação do SSA_Consulta_Rapida é uma solução madura com boa arquitetura em camadas e múltiplos mecanismos de fallback. Os principais pontos fortes são sua tolerância a variações de entrada e robustez contra falhas parciais.

Os principais problemas identificados são relacionados a performance em arquivos grandes (uso de memória) e algumas fragilidades em cenários de borda (caminhos de arquivo, encoding, datas ambíguas).

A prioridade de correção deve ser:
1. **Alta**: Vetorizar normalização SSA (impacto performance)
2. **Alta**: Adicionar checksum ao cache (confiabilidade)
3. **Média**: Implementar chunking na leitura (escalabilidade)
4. **Média**: Melhorar validação de datas (qualidade de dados)
5. **Baixa**: Sistema de schema versionado (manutenibilidade)

---

**Documentação gerada em**: 2025-03-01  
**Versão do sistema analisada**: 3.11+  
**Arquivos analisados**: 50+ módulos Python relacionados à importação
